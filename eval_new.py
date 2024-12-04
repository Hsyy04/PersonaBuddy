import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'PersonaBuddy.settings')
django.setup()
from agent.models import *

def lunshu(all_message):
    ret = {}
    cnt = 0
    for item in all_message:
        print(item)
        print("*"*18, cnt)
        if item.sender =="user":
            cnt += 1
        if item.has_action:
            ret[item] = cnt
            cnt = 0
    return ret

def get_edit_distance(s1, s2):
    # 初始化矩阵
    m, n = len(s1), len(s2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    
    # 初始化边界条件
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j
    
    # 填充矩阵
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if s1[i - 1] == s2[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = min(dp[i - 1][j] + 1,    # 删除
                               dp[i][j - 1] + 1,    # 插入
                               dp[i - 1][j - 1] + 1)  # 替换
    return dp[m][n]

def data_report(pid):
    # 该用户直接编辑规则数量
    direct_edit_add = Chilog.objects.filter(pid=pid, isbot=False, action_type="add").count()
    direct_edit_update = Chilog.objects.filter(pid=pid, isbot=False, action_type="update").count()
    direct_edit_delete = Chilog.objects.filter(pid=pid, isbot=False, action_type="delete").count()
    # 该用户通过bot编辑规则数量
    indirect_edit_add = Chilog.objects.filter(pid=pid, isbot=True, action_type="add").count()
    indirect_edit_update = Chilog.objects.filter(pid=pid, isbot=True, action_type="update").count()
    indirect_edit_delete = Chilog.objects.filter(pid=pid, isbot=True, action_type="delete").count()
    # 用户与各个模块对话的数量
    session_all = Session.objects.filter(pid=pid)
    session_align = session_all.filter(task='0')
    session_feedback = session_all.filter(task='2')
    message_align_count = Message.objects.filter(session__in=session_align).count()
    message_feedback_count = Message.objects.filter(session__in=session_feedback).count()
    # 用户通过各个模块编辑规则的数量
    align_edit_add = GenContentlog.objects.filter(pid=pid, is_ac=True, from_which_session__in=session_align, action_type="add").count()
    align_edit_delete = GenContentlog.objects.filter(pid=pid, is_ac=True, from_which_session__in=session_align, action_type="update").count()
    align_edit_update = GenContentlog.objects.filter(pid=pid, is_ac=True, from_which_session__in=session_align, action_type="delete").count()

    feedback_edit_add = GenContentlog.objects.filter(pid=pid, is_ac=True, from_which_session__in=session_feedback, action_type="add").count()
    feedback_edit_delete = GenContentlog.objects.filter(pid=pid, is_ac=True, from_which_session__in=session_feedback, action_type="update").count()
    feedback_edit_update = GenContentlog.objects.filter(pid=pid, is_ac=True, from_which_session__in=session_feedback, action_type="delete").count()

    # 用户产生被应用规则的轮数
    lunshu_dict_align = {}
    for session in session_align:
        all_message = Message.objects.filter(session=session)
        tem = lunshu(all_message)
        for key in tem:
            if key not in lunshu_dict_align:
                lunshu_dict_align[key] = tem[key]
            else:
                assert False
    lunshu_dict_align_rule = {}
    gen_rules = GenContentlog.objects.filter(pid=pid, is_ac=True, from_which_session__in=session_align)
    for one_rule in gen_rules:
        if one_rule.from_which_message in lunshu_dict_align:
            lunshu_dict_align_rule[one_rule.change_rule] = lunshu_dict_align[one_rule.from_which_message]
        else:
            print(one_rule.from_which_message)
            print(lunshu_dict_align)
            assert False
        
    lunshu_dict_feedback = {}
    for session in session_feedback:
        all_message = Message.objects.filter(session=session)
        tem = lunshu(all_message)
        for key in tem:
            if key not in lunshu_dict_feedback:
                lunshu_dict_feedback[key] = tem[key]
            else:
                assert False
    lunshu_dict_feedback_rule = {}
    gen_rules = GenContentlog.objects.filter(pid=pid, is_ac=True, from_which_session__in=session_feedback)
    for one_rule in gen_rules:
        if one_rule.from_which_message in lunshu_dict_feedback:
            lunshu_dict_feedback_rule[one_rule.change_rule] = lunshu_dict_feedback[one_rule.from_which_message]
        else:
            assert False

    # 每个规则过滤不是内容的数量
    record_all = Record.objects.filter(pid=pid, filter_result=True)
    rule_filtercount = {}
    for one_rule in record_all:
        if one_rule.context not in rule_filtercount:
            rule_filtercount[one_rule.context] = 1
        else:
            rule_filtercount[one_rule.context] += 1
    
    # 间接管理的接受率
    bot_rule = GenContentlog.objects.filter(pid=pid)
    if bot_rule.count() == 0:
        print(f"{pid} no bot rule!!!!!!")
        acc = f"{pid} 没有通过聊天配置!!!!!!"
    else:
        bot_rule_accept = bot_rule.filter(is_ac=True).count()
        bot_rule_all = bot_rule.count()
        acc = bot_rule_accept/float(bot_rule_all)

    # 间接管理的编辑距离
    rule_edit_dis = {}
    for one_rule in bot_rule:
        if one_rule.action_type != "delete":
            edit_dis = get_edit_distance(one_rule.new_rule, one_rule.change_rule)
            rule_edit_dis[one_rule.change_rule] = edit_dis

    # 处理指标格式
    return {
        "direct_add": direct_edit_add,
        "direct_update": direct_edit_update,
        "direct_delete": direct_edit_delete,
        "indirect_add": indirect_edit_add,
        "indirect_update": indirect_edit_update,
        "indirect_delete": indirect_edit_delete,
        "message_align_count": message_align_count,
        "message_feedback_count": message_feedback_count,

        "align_add": align_edit_add,
        "align_update": align_edit_update,
        "align_delete": align_edit_delete,
        "feedback_add": feedback_edit_add,
        "feedback_update": feedback_edit_update,
        "feedback_delete": feedback_edit_delete,

        "lunshu_align": lunshu_dict_align_rule,
        "lunshu_feedback": lunshu_dict_feedback_rule,

        "rule_filtercount": rule_filtercount,

        "bot_rule_acc":acc,
        "rule_edit_dis":rule_edit_dis
    }

import json
if __name__ == "__main__":
    all_user = UserPid.objects.all()
    print(all_user)
    # assert False
    for one_user in all_user:
        data = data_report(one_user.pid)
        print(data)
        with open(f"logs/{one_user.pid}.json","w+") as f:
            f.write(json.dumps(data))
        print(f"{one_user.pid}.json done")

    
