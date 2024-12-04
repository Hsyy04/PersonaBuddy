import json
import re
from .prompt_utils import get_bailian_response, get_common_response, get_clean_items, DIALOG_MODEL, extract_code_blocks
import logging
logger = logging.getLogger("myapp")
from  retry import retry

HAS_ACTION_PROMPT = """一位用户希望调整平台推荐给他的个性化列表，于是他与客服进行了如下对话：
{messages}

根据对话内容，你能否分析出该用户想看或不想看什么类型的内容？注意，请重点依据“用户”的消息进行推断, 不要揣测用户想法，仅根据字面意思判断，例如用户只是询问理由，不代表他不想看某类内容。

请你以json格式回复，它包含3个字段：
- analysis：字符串格式，值代表你对该问题的分析
- choice：字符串格式，值代表你的答案；注意，你只能在下面三个字符串中选一个作为回复："能分析出用户想看的内容", "能分析出用户不想看的内容", "不能分析出"
- needs：字符串格式，值代表你分析出的用户需求；注意，如果choice的值为"能分析出用户想看的内容"，则该字段的值应以“用户想看”开头；如果choice的值为"能分析出用户不想看的内容"，则该字段的值应该以“用户不想看”开头；如果choice的值为"不能分析出"，则该字段的值为空字符串

请严格按照以下格式返回结果：
{{
    "analysis": "<你对该问题的分析>",
    "choice": "<你的答案（能分析出用户想看的内容/能分析出用户不想看的内容/不能分析出）>",
    "needs" "<你分析出的用户需求（用户想看/用户不想看/空字符串）>"
}}
"""
def get_has_action(messages):
    '''
     返回 has_likes, has_dislikes, histories 
    '''
    histories = [{"role": "user", "content": HAS_ACTION_PROMPT.format(messages=messages)}]
    log_str = "******check has action prompt********\n"
    log_str += str(histories)+"\n"
    response = get_bailian_response(histories, model=DIALOG_MODEL)
    log_str+= "*****begin to print response.*****\n"
    log_str+= str(response) + "\n"
    log_str+= "*****end to print response.*****\n"
    logger.debug(log_str)
    histories.append({"role": "assistant", "content": response})

    try:
        if response.startswith("```"):
            res = json.loads(extract_code_blocks(response,"json"))
        else:
            res = json.loads(response)
        choice , needs = res["choice"], res["needs"]
    except:
        logger.error("get_has_action: json.loads error")
        print(response)
        return False, False, histories, response, None
    has_likes =True if "想看的内容" in choice else False
    has_dislikes = True if "不想看的内容" in choice else False
    return has_likes, has_dislikes, histories, response, needs


ANALYSE_RULES_PROMPT ='''目前，用户已经定义了如下{count}条规则：
{rules}

上述你刚总结出用户需求“{needs}”是否与这{count}条存在关联？请逐条分析一下。

请你以json格式回复，严格按照以下格式返回结果：
{{
    "answer": [
        {{"rule_id": "<规则编号1>", "analysis": "<新需求与该规则的关联1>"}},
        {{"rule_id": "<规则编号2>", "analysis": "<新需求与该规则的关联2>"}},
        ...
    ]
}}
'''
def get_analyse_rules(rules, count, histories, needs):
    histories.append({"role": "user", "content": ANALYSE_RULES_PROMPT.format(rules=rules, count=count, needs=needs)})
    log_str = "******check analyse rules prompt********\n"
    log_str += str(histories)+"\n"
    response = get_bailian_response(histories, model=DIALOG_MODEL)
    log_str+= "*****begin to print analyse rules.*****\n"
    log_str+= str(response) + "\n"
    log_str+= "*****end to print analyse rules.*****\n"
    logger.debug(log_str)

    histories.append({"role": "assistant", "content": response})
    return response, histories

# 生成新增或添加的指令
CHANGE_RULES_PROMPT = """根据你的分析，请你告诉我应该如何操作已有的规则，以将你新总结的用户需求“{needs}”加入到规则列表中。你可以进行“新增”和“更新”两种操作：
1、当你新总结的用户需求与任意一条已有规则的关联性都很小时，你可以选择“新增”一条规则。
2、为了避免重复并保持规则列表的简洁性，当你新总结的用户需求与某一条已有规则的关联性很大时，你可以选择“更新”该已有规则。

请你以json格式回复，它包含4个字段：
- analysis：字符串格式，值代表你对该问题的分析
- choice：字符串格式，值代表你的答案；注意，你只能在下面两个字符串中选一个作为回复："新增", "更新"
- rule_id：字符串格式，如果choice的值为"更新"，则该字段的值代表要更新的规则的id；如果choice的值为"新增"，则该字段为空字符串
- rule：字符串格式，根据choice的值，该字段的值为将你总结的新需求合并到rule_id所对应的规则中后新生成的规则，或者根据你总结的新需求新增的规则，请以“我不想看”开头

请严格按照以下格式返回结果：
{{
    "analysis": "<你对该问题的分析>",
    "choice": "<你的答案（新增/更新）>",
    "rule_id": "<规则编号/空字符串>",
    "rule": <更新或新增的规则内容（我不想看）>
}}
"""
@retry(tries=3, delay=1, backoff=2)
def get_change_rules(histories, needs):
    '''
    return need_add, need_update, histories, change_item 
    '''
    histories.append({"role": "user", "content": CHANGE_RULES_PROMPT.format(needs=needs)})
    log_str = "******check change rules prompt********\n"
    log_str += str(histories)+"\n"
    response = get_bailian_response(histories, model=DIALOG_MODEL)
    log_str+= "*****begin to print rules.*****\n"
    log_str+= str(response) + "\n"
    log_str+= "*****end to print rules.*****\n"
    logger.debug(log_str)

    if response.startswith("对不起"):
        return False, False, histories, None, None
    if response.startswith("```"):
        data = json.loads(extract_code_blocks(response,"json"))
    else:
        data = json.loads(response)
    analysis = data['analysis']
    choice = data['choice']
    rule_id = data['rule_id']
    rule = data['rule']

    need_add = True if "新增" in choice else False
    need_update = True if "更新" in choice else False
    if need_add:
        return need_add, need_update, histories, None, rule
    if need_update:
        update_id = re.findall(r'\d+', rule_id)
        if len(update_id) > 0:
            update_id=update_id[0]
        print("update_id:", update_id)
        return need_add, need_update, histories, update_id, rule
    return need_add, need_update, histories, None, rule


DEL_RULES_PROMPT ="""根据你的分析，请你告诉我应该如何操作已有的规则，以将你分析出的用户需求“{needs}”加入到用户的规则列表中。你可以进行“删除”“更新”和“无”三种操作：
1、当你新总结的用户需求与某一条已有规则关联性很大且完全矛盾，你可以选择“删除”该已有规则。
2、当你新总结的用户需求与某一条已有规则关联性很大且并不完全矛盾，可以通过对该规则进行细化而将二者统一起来，你可以选择“更新”该已有规则。
3、当你新总结的用户需求与任意一条已有规则的关联性都很小时，你可以选择“无”，此时不需要对规则列表进行任何操作。

请你以json格式回复，它包含4个字段：
- analysis：字符串格式，值代表你对该问题的分析
- choice：字符串格式，值代表你的答案；注意，你只能在下面三个字符串中选一个作为回复："删除", "更新", "无"
- rule_id：字符串格式，如果choice的值为"更新"或"删除"，则该字段的值代表要更新或删除的规则的id；如果choice的值为"无"，则该字段为空字符串
- rule：字符串格式，如果choice的值为"更新"，该字段的值为将你总结的新需求合并到rule_id所对应的规则中后新生成的规则，请以“我不想看”开头；如果choice为"删除"或"无"，该字段为空字符串

请严格按照以下格式返回结果：
{{
    "analysis": "<你对该问题的分析>",
    "choice": "<你的答案（删除/更新/无）>",
    "rule_id": "<规则编号/空字符串>",
    "rule": <更新的规则内容（我不想看）/空字符串>
}}
"""
@retry(tries=3, delay=1, backoff=2)
def get_contradiction_rules(histories, needs):
    histories.append({"role": "user", "content": DEL_RULES_PROMPT.format(needs=needs)})
    log_str = "******check contradiction rules prompt********\n"
    log_str += str(histories)+"\n"
    response = get_bailian_response(histories, model=DIALOG_MODEL)
    log_str+= "*****begin to print rules.*****\n"
    log_str+= str(response) + "\n"
    log_str+= "*****end to print rules.*****\n"
    logger.debug(log_str)

    if response.startswith("对不起"):
        return False, False, histories, None, None

    if response.startswith("```"):
        data = json.loads(extract_code_blocks(response,"json"))
    else:
        data = json.loads(response)
    analysis = data['analysis']
    choice = data['choice']
    rule_id = data['rule_id']
    rule = data['rule']

    need_del = True if "删除" in choice else False
    need_update = True if "更新" in choice else False
    if need_del:
        del_id = re.findall(r'\d+', rule_id)
        return need_del, need_update, del_id[0], rule
    if need_update:
        update_id = re.findall(r'\d+', rule_id)
        return need_del, need_update, update_id[0], rule
    return False, False, None, None

def get_fuzzy(chat_history, rules, platform=None, pid=None, max_iid=-1):
    '''
        chat_history: "user:xxx\nassistant:xxx\nuser:xxx\n..."
        personalities: ""
        rules: json, "[{'iid': 1, 'platform': 1, 'rule': 'summary', 'pid': 1, 'isactive': True}...]"

        返回: response(str), action_list: json, "{'type': 1, 'profile': {'iid': 1, 'platform': 1, 'rule': 'summary', 'pid': 1, 'isactive': True}, 'keywords': ['k1','k2']}\n..."
    '''
    count = len(rules)
    rules_str = ""
    id_to_iid = []
    next_iid = max_iid
    for i, rule in enumerate(rules):
        rule = rule['fields']
        rules_str += f"{i+1}."+ rule['rule'] + "\n"
        id_to_iid.append(rule['iid'])

    has_likes, has_dislikes, histories, resp, needs = get_has_action(messages=chat_history)
    if has_dislikes:
        analyse, histories = get_analyse_rules(rules_str.strip(), count, histories, needs)

        actions= []
        need_add, need_update, histories, update_id, new_rule= get_change_rules(histories, needs)
        print("need_update, need_add, update_id:", need_update, need_add, update_id)
        logger.warn("need_update, need_add, update_id: %s, %s, %s", need_update, need_add, update_id)
        if need_add:
            actions.append({"type":1, "profile": {"iid": next_iid, "platform": platform, "rule": new_rule, "pid": pid, "isactive": True}, 'keywords':[]})
        elif need_update and (update_id is not None):
            actions.append({"type":2, "profile": {"iid": id_to_iid[int(update_id)-1], "platform": platform, "rule": new_rule, "pid": pid, "isactive": True}, 'keywords':[]})
        else:
            logger.error("fuzzy 有不想看需求 但是 没有新增或者更新")
            response = get_common_response(chat_history)
            return response, []
        return "", actions
    elif has_likes:
        analyse, histories = get_analyse_rules(rules_str.strip(), count, histories, needs)
        need_del, need_update, operate_id, new_rule = get_contradiction_rules(histories, needs)
        if need_del:
            actions = [{"type":3, "profile": {"iid": id_to_iid[int(operate_id)-1], "platform": platform, "rule": rules[int(operate_id)-1]['fields']['rule'], "pid": pid, "isactive": False}, 'keywords':[]}]
        elif need_update:# FIXME:elif need_update and (update_id is not None):
            actions = [{"type":2, "profile": {"iid": id_to_iid[int(operate_id)-1], "platform": platform, "rule": new_rule, "pid": pid, "isactive": True}, 'keywords':[]}]
        else:
            actions = []
            logger.error("fuzzy 有想看需求 但是 没有删除或者更新")
            response = get_common_response(chat_history)
            return response, []
        return "", actions
    else:
        response = get_common_response(chat_history)
        return response, []

if __name__ == "__main__":
    chathistory = [{'role': 'user', 'content': '一位用户希望调整平台推荐给他的个性化列表，于是他与客服进行了如下对话.\n聊天上下文:\n客服:根据**平台推荐**，你可能喜欢\n1. 孙颖莎比赛策略分析\n2. 形象与社交关系\n3. 程序员行为特征\n4. Java版本更新关注\n5. 蔡澜饮食文化观点\n6. 深度算子网络理解\n7. 个人对深度学习态度\n8. 家庭教育与子女性格\n9. 论文创新与方法整合\n10. 程序员硬件偏好\n\n 而你都没有点击, 是不是不喜欢这些内容？\n用户: 你好，你能为我做些什么？\n\n根据当前的对话(请重点关注"用户"消息)，你能否分析出该用户想看或不想看什么类型的内容吗？注意，只是用对话中的信息进行分析。\n你的回复应该包括两行，第一行应在下面三句话中选一个作为回复：“能分析出用户想看的内容”“能分析出用户不想看的内容”或“不能分析出”，第二行回复你给出答案的原因。分析原因时，你只需要做简单的扩展，不要过度揣测用户的想法。'}, {'role': 'assistant', 'content': '能分析出用户不想看的内容\n\n原因：用户在对话开头没有直接回答客服的问题，而是询问了客服能为他做什么。这表明用户对当前推荐的内容不感兴趣，希望通过与客服的交流来调整推荐列表，找到更符合他需求的内容。'}, {'role': 'user', 'content': '平台允许用户自定义一些规则来屏蔽不想看的内容，请你根据用户需求和你的分析，帮助用户生成一条过滤规则.\n以“我不想看XXX”开头.注意输出不要重复，越简洁越好.'}, {'role': 'assistant', 'content': '我不想看孙颖莎比赛策略分析,形象与社交关系,程序员行为特征,Java版本更新关注,蔡澜饮食文化观点,深度算子网络理解,个人对深度学习态度,家庭教育与子女性格,论文创新与方法整合,程序员硬件偏好'}, {'role': 'user', 'content': '目前，用户已经定义了如下1条规则：\n1.我不想看与计算机相关的话题\n\n根据你的分析, 上述总结出的规则是否与这1条存在关联？请逐条分析一下。注意语言应该简单明了，不要输出额外的内容。'}, {'role': 'assistant', 'content': '存在关联。\n\n1. "我不想看与计算机相关的话题" 这个规则与用户的兴趣相符，因为用户没有点击任何与编程、Java版本更新、程序员行为特征或程序员硬件偏好相关的条目，这些都是与计算机相关的话题。这条规则有效地概括了用户可能不感兴趣的主题，即与计算机和编程有关的内容。'}, {'role': 'user', 'content': '如你分析的那样，新规则可能与已有规则存在关联。根据你的分析，请你告诉我应该如何操作已有的规则，以将你新总结的规则加入到用户的规则列表中。你可以进行下面两种操作：\n1、当新规则与某一条已有规则的关联性很大时，包括二者的含义一致或矛盾两种情况，你可以选择“更新”该已有规则。\n2、当新规则与任意一条已有规则的关联性都很小时，你可以选择“新增”该规则\n你的回复应该包括两行或三行。第一行回复“更新”或“新增”。如果第一行回复“更新”，你应在第二行回复要更新的已有规则的编号，并在第三行告诉我理由。如果第一行回复的是“新增”，你应在第二行告诉我理由。'}]
    
    get_change_rules(chathistory)