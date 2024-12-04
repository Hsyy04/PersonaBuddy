import json
from django.http import JsonResponse
from django.core import serializers
import logging
logger = logging.getLogger("myapp")

from agent.prompt.prompt_utils import interval
from .const import SUCCESS, FAILURE, PLATFORM_CHOICES, PLATFORMS
from .models import *
import random
from .prompt.filter import filter_item
from .prompt.fuzzy import get_fuzzy
from .prompt.alignment import get_simple_personalities_from_browses, get_simple_personalities_from_clicks

from .utils import build_response, feedback_to_response, get_his_message_str,get_browses_wc, get_clicks_wc


def browse(request):
    """监控推荐记录+依上下文操纵呈现内容"""
    if request.method == 'POST':
        params = json.loads(request.body)
        all_rules = Rule.objects.filter(pid=params['pid'], platform=PLATFORM_CHOICES[params['platform']][0], isactive=True)
        all_rules_json = json.loads(serializers.serialize('json', all_rules)) 
        interaction = Record(pid=params['pid'],
                             platform=PLATFORM_CHOICES[params['platform']][0],
                             title=params['title'],
                             content=params['content'],
                             url=params['url'],
                             is_filter=params['is_filter'])
        data = 0
        if params['is_filter']:
            filter_result, filter_reason, rule = filter_item(all_rules_json, params['title'])
            data = filter_result
            interaction.filter_result = filter_result
            interaction.filter_reason = filter_reason
            interaction.context = rule 
        interaction.save()
        return build_response(SUCCESS, data)
    
def click(request):
    """监控用户行为"""
    if request.method == 'POST':
        params = json.loads(request.body)
        interaction = Record.objects.filter(pid=params['pid'],
                                            platform=PLATFORM_CHOICES[params['platform']][0],
                                            title=params['title']).order_by('-browse_time').first()

        interaction.click = True
        interaction.save()
        return build_response(SUCCESS, None)
    
def report(request):
    """报表"""
    if request.method == 'GET':
        sk = request.validated_params['sk']
        interactions = Record.objects.filter(key=sk)
        interactions_dict_list = [{
            'key': interaction.key,
            'content': interaction.content,
            'click': interaction.click,
            'label_result': interaction.label_result,
            'browse_time': interaction.browse_time,
            'click_time': interaction.click_time,
        } for interaction in interactions]
        return build_response('成功', SUCCESS, interactions_dict_list)
    
def dialogue(request):
    """与用户对话"""
    data = json.loads(request.body)
    sid = data['sid']
    pid = data['pid']
    content = data['content']
    task = data['task']
    platform = PLATFORM_CHOICES[data['platform']][0]

    # 新建一条用户消息
    try:
        session = Session.objects.get(id=sid)
    except:
        session = Session(pid=pid, task=task, platform=platform, summary="This is a session")
        session.save()
        sid = session.id
        if task == 0:
            personalities = Personalities.objects.filter(pid=pid, platform=platform)
            if len(personalities) != 0:
                personalities = personalities.first()
                sys_message = Message(session=session, content=personalities.first_response, sender='bot')
                sys_message.save()
        elif task ==2:
            first_response = feedback_to_response(pid, platform)
            sys_message = Message(session=session, content=first_response, sender='bot')
            sys_message.save()

    message = Message(session=session, content=content, sender='user')
    message.save()
    # 获取历史
    messges_str = get_his_message_str(sid)
    
    # 获取规则
    platform_id = PLATFORMS.index(platform)
    rules = Rule.objects.filter(pid=pid, platform=platform)
    active_rule = rules.filter(isactive=True)
    rules_json = json.loads(serializers.serialize('json', active_rule))

    # 设置下一条item的iid
    next_iid = -1
    for rule in rules:
        if rule.iid > next_iid:
            next_iid = rule.iid
    next_iid += 1
    response, actions = get_fuzzy(chat_history=messges_str, rules=rules_json, platform=platform_id, pid=pid, max_iid=next_iid)

    # 这里需要记录一下生成的search行为
    # 以及这里需要记录一下生成的规则
    for action in actions:
        if action['type'] == 4:
            search = Searchlog.objects.create(pid=pid, platform=platform, gen_keyword=action['keywords'][0], is_accepted=False)
            action['log_id'] = search.id
        elif action['type'] == 1:
            gen_content = GenContentlog.objects.create(pid=pid, action_type='add', platform=platform, new_rule=action['profile']['rule'], old_rule='', is_ac=False, change_rule='', from_which_session=session)
            action['log_id'] = gen_content.id
        elif action['type'] == 3:
            rule_id = action['profile']['iid']
            old_rule = Rule.objects.filter(pid=pid, iid=rule_id).first().rule
            gen_content = GenContentlog.objects.create(pid=pid, action_type='update', platform=platform, new_rule=action['profile']['rule'], old_rule=old_rule, is_ac=False, change_rule='', from_which_session=session)
            action['log_id'] = gen_content.id
        elif action['type'] == 2:
            rule_id = action['profile']['iid']
            old_rule = Rule.objects.filter(pid=pid, iid=rule_id).first().rule
            gen_content = GenContentlog.objects.create(pid=pid, action_type='delete', platform=platform, new_rule='', old_rule=old_rule, is_ac=False, change_rule='', from_which_session=session)
            action['log_id'] = gen_content.id
        else:
            pass

    # 更新message.
    if len(actions) == 0:
        bot_message = Message(session=session, content=response, sender='bot')
        bot_message.save()
    return build_response(SUCCESS,{
        "content": response, 
        "sid": session.id,
        "action":actions,
        "task":session.task,
        "platform":PLATFORMS.index(session.platform),
        "pid":session.pid,
        "summary": session.summary
    })

def get_sessions(request):
    if request.method == "POST":
        data = json.loads(request.body)
        pid = data['pid']
        task = data['task']

        sessions = Session.objects.filter(pid=pid, task=task)
        session_list =[]
        for session in sessions:
            session_list.append({
                'sid': session.id,
                "platform": PLATFORMS.index(session.platform),
                "task": int(session.task),
                'summary': session.summary
            })
        return build_response(SUCCESS, {"sessions": session_list})
    return build_response(FAILURE, {"sessions": []})

def save_rules(request):
    if request.method == "POST":
        data = json.loads(request.body)
        isbot = data['isbot']
        isdel = data['isdel']
        rule = data['rule']
        rule_id = data['iid']
        pid = data['pid']

        target_rules = Rule.objects.filter(pid=pid, iid=rule_id)
        if not isdel:
            if len(target_rules) == 0:
                # 说明是增加
                new_rule = Rule.objects.create(iid=rule['iid'], pid=pid, rule=rule['rule'], isactive=rule['isactive'], platform=PLATFORM_CHOICES[rule['platform']][0])
                # 记录Chilog
                chilog = Chilog.objects.create(pid=pid, platform=PLATFORM_CHOICES[rule['platform']][0], iid=rule['iid'], rule=rule['rule'], isactive=rule['isactive'], action_type='add', isbot=isbot)
            elif target_rules.first().rule != rule['rule'] or target_rules.first().isactive != rule['isactive'] or target_rules.first().platform != PLATFORM_CHOICES[rule['platform']][0]:
                # 说明是更新
                target_rules.update(rule=rule['rule'], isactive=rule['isactive'], platform=PLATFORM_CHOICES[rule['platform']][0])
                # 记录Chilog
                chilog = Chilog.objects.create(pid=pid, platform=PLATFORM_CHOICES[rule['platform']][0], iid=rule['iid'], rule=rule['rule'], isactive=rule['isactive'], action_type='update', isbot=isbot)
        else:  
            target_rules.delete()
            chilog = Chilog.objects.create(pid=pid, iid=rule_id, action_type='delete', isbot=isbot)

        logger.info(f"save rules of {pid}: {Rule.objects.filter(pid=pid)}")
        return build_response(SUCCESS, None)
    return build_response(FAILURE, None)
    
def get_history(request, sid):
    if request.method == "GET":
        messages = Message.objects.filter(session=sid).order_by('timestamp')
        messages_list = []
        for message in messages:
            messages_list.append({
                "content": message.content,
                "sender": message.sender,
            })
        return build_response(SUCCESS, {"messages": messages_list})
    return build_response(FAILURE, None)

def save_search(request):
    if request.method == "POST":
        data = json.loads(request.body)
        pid = data['pid']
        platform = PLATFORM_CHOICES[data['platform']][0]
        keyword = data['keyword']
        search = Searchlog(pid=pid, platform=platform, keyword=keyword, is_accepted=True)
        search.save()
        return build_response(SUCCESS, None)
    return build_response(FAILURE, None)

def get_alignment(request):
    data = json.loads(request.body)
    platform = PLATFORM_CHOICES[data['platform']][0]
    pid = data['pid']
    browses = Record.objects.filter(pid=pid, platform=platform, is_filter=True).order_by('-browse_time')
    if len(browses) == 0:
        return build_response(SUCCESS, {"personalities": [], "response": "你最近没有浏览记录"})
    
    browses_title = [browse.title for browse in browses[:min(10, len(browses))]]

    clicks = browses.filter(click=True)
    click_titles = [click.title for click in clicks[:min(10, len(clicks))]]
    try:
        print("query one personalities...")
        now_personality = Personalities.objects.filter(pid=pid, platform=platform).first()
        if browses[0].browse_time <= now_personality.update_time and clicks[0].click_time <= now_personality.update_time:
            return build_response(SUCCESS, {"personalities": now_personality.personality, "response": now_personality.first_response})
        else:
            personalities = get_simple_personalities_from_browses(browses=browses_title).strip()
            # personality_click = get_simple_personalities_from_clicks(clicks=click_titles).strip()
            try:
                personality_click = PersonalitiesClick.objects.filter(pid=pid, platform=platform).first().personality_click
                assert len(personality_click)>0
            except:
                if len(click_titles)>0:
                    personality_click = get_simple_personalities_from_clicks(clicks=click_titles).strip()
                else:
                    personality_click=""     
            if len(click_titles)>0:       
                first_response = f"根据**平台推荐**，你可能喜欢\n{personalities}\n\n 而根据你的**点击内容**，我猜你的偏好是\n{personality_click}\n\n 请问有什么可以帮助你的吗？"
            else:
                first_response = f"根据**平台推荐**，你可能喜欢\n{personalities}\n\n 而你都没有点击, 是不是不喜欢这些内容？"

            now_personality.personality_click = personality_click
            now_personality.personality = personalities
            now_personality.first_response = first_response
            now_personality.save()
            return build_response(SUCCESS, {"personalities": now_personality.personality, "response": now_personality.first_response})
    except:
        personalities = get_simple_personalities_from_browses(browses=browses_title).strip()
        try:
            personality_click = PersonalitiesClick.objects.filter(pid=pid, platform=platform).first().personality_click
            assert len(personality_click)>0
        except:
            if (len(click_titles)>0):
                personality_click = get_simple_personalities_from_clicks(clicks=click_titles).strip()
            else:
                personality_click=""
        if len(click_titles)>0:       
            first_response = f"根据**平台推荐**，你可能喜欢\n{personalities}\n\n 而根据你的**点击内容**，我猜你的偏好是\n{personality_click}\n\n 请问有什么可以帮助你的吗？"
        else:
            first_response = f"根据**平台推荐**，你可能喜欢\n{personalities}\n\n 而你都没有点击, 是不是不喜欢这些内容？"
        now_personality = Personalities(pid=pid, platform=platform, personality=personalities, personality_click=personality_click, first_response=first_response)
        now_personality.save()
        return build_response(SUCCESS, {"personalities": now_personality.personality, "response": now_personality.first_response})

def get_feedback(request):
    data = json.loads(request.body)
    platform = PLATFORM_CHOICES[data['platform']][0]
    pid = data['pid']
    response = feedback_to_response(pid, platform)
    return build_response(SUCCESS, {"response": response}) 

def make_new_message(request):
    if request.method == "POST":
        data = json.loads(request.body)
        pid = data['pid']
        sid = data['sid']
        platform = PLATFORM_CHOICES[data['platform']][0]
        ac_actions = data['ac_actions']
        wa_actions = data['wa_actions']

        now_session = Session.objects.filter(id=sid, pid=pid, platform=platform)
        if len(now_session) == 0:
            return build_response(FAILURE, None)
        now_session = now_session.first()
        message_content = ""
        if len(ac_actions) != 0:
            message_content += "我帮你完成了如下操作:\n\n"
            for action in ac_actions:
                if action['type'] == 1:
                    message_content += f"* 新增规则: {action['profile']['rule']} \n"
                elif action['type'] == 3:
                    message_content += f"* 删除规则: {action['profile']['rule']} \n"
                elif action['type'] == 2:
                    message_content += f"* 更新规则: {action['profile']['rule']} \n"
                elif action['type'] == 4:
                    message_content += f"* 搜索关键词: {action['keywords'][0]} \n"
            message_content += "\n"
        if len(wa_actions) != 0:
            message_content += "但是看起来，你并不希望我帮你:\n\n"
            for action in wa_actions:
                if action['type'] == 1:
                    message_content += f"* 新增规则: {action['profile']['rule']} \n"
                elif action['type'] == 3:
                    message_content += f"* 删除规则: {action['profile']['rule']} \n"
                elif action['type'] == 2:
                    message_content += f"* 更新规则: {action['profile']['rule']} \n"
                elif action['type'] == 4:
                    message_content += f"* 搜索关键词: {action['keywords'][0]} \n"
        message = Message(session=now_session, content=message_content, sender='assistant', has_action=(len(ac_actions)!=0))
        message.save()

        # 这里简单示意一个session的总结
        now_session=Session.objects.get(id=sid)
        now_session.summary = message_content
        now_session.save()

        # 更新log
        for action in (ac_actions):
            if action['type'] == 4:
                search = Searchlog.objects.get(id=action['log_id'])
                search.is_accepted = True
                search.edited_keyword = action['keywords'][0]
                search.save()
            elif action['type'] in [1, 2, 3]:
                gen_content = GenContentlog.objects.get(id=action['log_id'])
                gen_content.is_ac = True
                gen_content.change_rule = action['profile']['rule']
                gen_content.from_which_message = message
                gen_content.save()
                logger.info("新的操作:"+serializers.serialize('json', [gen_content]))
                print("新的操作:"+serializers.serialize('json', [gen_content]))

        for action in (wa_actions):
            if action['type'] == 4:
                search = Searchlog.objects.get(id=action['log_id'])
                search.is_accepted = False
                search.edited_keyword = action['keywords'][0]
                search.save()
            elif action['type'] in [1, 2, 3]:
                gen_content = GenContentlog.objects.get(id=action['log_id'])
                gen_content.is_ac = False
                gen_content.change_rule = action['profile']['rule']
                gen_content.from_which_message = message
                gen_content.save()
                logger.info("新的操作:"+serializers.serialize('json', [gen_content]))
                print("新的操作:"+serializers.serialize('json', [gen_content]))
                
        return build_response(SUCCESS, {
            "content": message.content,
            "sender": message.sender,
        })
    
def get_word_count(request):
    # return word cloud, 传入参数可能是浏览的，也可能是click
    '''
    wc =[{word:xxx, count:xxx}]
    '''
    data = json.loads(request.body)
    pid = data['pid']
    type = data['type']
    platform = PLATFORM_CHOICES[data['platform']][0]
    if type == "browse":
        # 获取浏览记录
        data = get_browses_wc(pid, platform, count=10)
        return_data = [{"text": key, "value": value} for key, value in data.items()]
        return build_response(SUCCESS, return_data)
    elif type == "click":
        # 获取点击记录
        data = get_clicks_wc(pid, platform, count=10)
        return_data = [{"text": key, "value": value} for key, value in data.items()]
        return build_response(SUCCESS, return_data)
    return build_response(FAILURE, None)

def record_user(request):
    logger.debug(f"connect user:{json.loads(request.body)['pid']}")
    pid = json.loads(request.body)['pid']
    try:
        UserPid.objects.get(pid=pid)
        Rule.objects.filter(pid=pid).delete()
    except:
        logger.debug(f"create new user: {pid}")
        UserPid.objects.create(pid=pid)
        
    profiles = json.loads(request.body)['profiles']
    for profile in profiles:
        Rule.objects.create(iid=profile['iid'], pid=pid, rule=profile['rule'], isactive=profile['isactive'], platform=PLATFORM_CHOICES[profile['platform']][0])

    logger.info(f"active user:{pid}, with profile: {Rule.objects.filter(pid=pid)}")
    return build_response(SUCCESS, None)

# 后面是用一个定时任务计算每个人的personalities
from apscheduler.schedulers.background import BackgroundScheduler
from django_apscheduler.jobstores import DjangoJobStore, register_events
from apscheduler.triggers.interval import IntervalTrigger
import time
import datetime as dt
from django_apscheduler.models import DjangoJobExecution
from .rah import get_rah_personalities

def set_rah_personalities():
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())+" start rah")
    all_pid = list(set([item.pid for item in UserPid.objects.all()]))
    logger.debug(f"all_pid: {all_pid}")
    platform = "知乎"
    is_new = False
    for pid in all_pid:
        last_personalities = PersonalitiesClick.objects.filter(pid=pid, platform=platform)
        if len(last_personalities) == 0:
            is_new = True
            last_personalities = PersonalitiesClick(pid=pid, platform=platform, personality_click="")
        else:
            last_personalities = last_personalities.first()
            logger.debug("last_personalities: "+serializers.serialize('json', [last_personalities]))
        records_all = Record.objects.filter(pid=pid, platform=platform, is_filter=True, filter_result=False).order_by('-browse_time')
        # 删除已经计算过的记录
        if not is_new:
            records_all = records_all.filter(browse_time__gt=last_personalities.update_time)
        logger.debug("还没有计算过的记录:")
        logger.debug(f"{records_all}")
        if len(records_all) == 0:
            continue

        # 分组， 需要保证每个组内的浏览时间不超过1min
        records_group = []
        one_group= []
        has_clicks = False
        earliest_time = records_all[0].browse_time
        for record in records_all:
            if record.browse_time - earliest_time > dt.timedelta(minutes=1):
                if len(one_group)!=0 and has_clicks:
                    records_group.append(one_group)
                one_group = []
                one_group.append(record)
                has_clicks = record.click
                earliest_time = record.browse_time
            else:
                has_clicks = (has_clicks or record.click)
                one_group.append(record)
        if len(one_group)!=0 and has_clicks:
            records_group.append(one_group)
        print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())+"开始分组采样并更新")
        logger.debug("(滑动窗口分组数)group num: "+str(len(records_group)))
        # 对于每个分组采样, 然后更新personalites
        for group in records_group:
            pos_records = [record.title for record in group if record.click]
            neg_records = [record.title for record in group if not record.click]
            click_personal = get_rah_personalities(pid, platform, pos_records, neg_records)
            if len(click_personal) == 0:
                continue
            last_personalities.personality_click = click_personal
            last_personalities.save()


def delete_old_job_executions(max_age=604_800):
    DjangoJobExecution.objects.delete_old_job_executions(max_age)

scheduler = BackgroundScheduler()
scheduler.add_jobstore(DjangoJobStore(), "default")

scheduler.add_job(
    set_rah_personalities,
    trigger=IntervalTrigger(minutes=interval),
    args=[],
    id='rah',
    max_instances=1,
    replace_existing=True,
)
register_events(scheduler)
scheduler.start()
# Hook into the apscheduler shutdown to delete old job executions
scheduler.add_listener(delete_old_job_executions, mask=2048)
