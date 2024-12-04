import json
import re
import logging
logger = logging.getLogger("myapp")

from .prompt_utils import get_bailian_response

from django.conf import settings


ANALYZE_PROMP ='''在在线问答平台上，有一个标题为 “{title}” 的问题，请你分析一下这个问题可能与哪些话题有关。注意：你的语言应简洁明了，不要过度扩展。''' 
def analyze_question(title, histories):
    histories.append({"role": "user", "content": ANALYZE_PROMP.format(title=title)})
    log_str = f"******check filter prompt********\n"
    log_str += f"{histories}\n"
    response = get_bailian_response(histories)
    log_str += f"********begin to print response{title}********\n"
    log_str += f"{response}\n"
    log_str += f"********end to print response********\n"
    logger.debug(log_str)
    histories.append({"role": "assistant", "content": response})
    return response, histories

JUDGE_PROMPT = '''在线问答平台的一个用户表达了“{rule}”的需求。为满足该用户的需求，你认为是否应该为该用户屏蔽“{title}”这个问题？请仅依据你的上述分析、通过该需求与问题的直接关联性进行判断，不要考虑间接关联，不要进行任何额外的拓展或考虑其它因素（例如平台推荐内容的多样性）。注意，但凡这个问题所关联的话题对于“{rule}”这一需求有所涉及，都应该被屏蔽。
注意，你的回复应该包括两行，第一行回复“是”或“否”，第二行回复你给出答案的理由。'''
def judge_item(title, rule, histories):
    logger.debug("******check filter prompt********")
    logger.debug(histories+[{"role": "user", "content": JUDGE_PROMPT.format(title=title, rule=rule)}])
    print(histories+[{"role": "user", "content": JUDGE_PROMPT.format(title=title, rule=rule)}])
    response = get_bailian_response(histories+[{"role": "user", "content": JUDGE_PROMPT.format(title=title, rule=rule)}], model="qwen-turbo")
    logger.debug(f"********begin to print response{title}********")
    logger.debug(response)
    print(response)
    logger.debug("********end to print response********")

    # 提取结果, 理由， 规则
    filter_result = False
    filter_reason = ""
    try:
        if response == "对不起，我无法帮助你":
            filter_reason = "DataInspectionFailed"
            filter_result = False
            return filter_result, filter_reason
        if len(response.split("\n")) < 2:
            response = response.strip()
            filter_result = True if response[0]=='是' else False
            filter_reason = response[2:]
            return filter_result, filter_reason

        filter_result = True if "是" in response.split("\n")[0] else False
        filter_reason = '\n'.join(response.split("\n")[1:])
    except:
        pass
    return filter_result, filter_reason

def filter_item(context, title):
    # TODO: 如果格式不对的异常处理!
    filter_result = False
    filter_rule = ""
    filter_reason = "没有配置规则"
    if len(context)==0:
        logger.warn(f"由于{filter_reason}, 用{filter_rule}判断{title}的结果是{filter_result}")
        print(f"由于{filter_reason}, 用{filter_rule}判断{title}的结果是{filter_result}")
        return filter_result, filter_reason, filter_rule
    analyse, histories = analyze_question(title, [])

    non_filter_reason = ""
    for rule in context:
        rule = rule['fields']['rule']
        # analyse, histories_new = analyze_rule(rule, histories)
        filter_result, filter_reason = judge_item(title, rule, histories)
        if filter_result == True:
            logger.warn(f"由于{filter_reason}, 用<{rule}>判断“{title}”的结果是 {filter_result}")
        else:
            logger.info(f"由于{filter_reason}, 用<{rule}>判断“{title}”的结果是 {filter_result}")

        print(f"由于{filter_reason}, 用<{rule}>判断“{title}”的结果是 {filter_result}")
        if filter_result == True:
            filter_rule = rule
            return filter_result, filter_reason, filter_rule
        non_filter_reason += f"由于{filter_reason}, 用<{rule}>判断“{title}”的结果是 {filter_result}\n\n"
    return filter_result, non_filter_reason, filter_rule


if __name__ == "__main__":
    histories = [{'role': 'user', 'content': '在在线问答平台上，有一个标题为 “娱乐圈真的所有女艺人都被潜规则过吗？” 的问题，请你分析一下这个问题可能与哪些话题有关。注意：你的语言应简洁明了，不要过度扩展。'}, {'role': 'assistant', 'content': '这个问题主要涉及以下几个话题：\n\n1. **娱乐圈文化**：探讨娱乐圈内的工作环境、职业规范和行业风气。\n2. **性别平等**：讨论女性在娱乐行业所面临的不平等待遇，包括但不限于薪酬差距、晋升机会和性骚扰等问题。\n3. **潜规则**：深入探讨“潜规则”这一概念在娱乐圈的含义，即不公开但普遍存在的行为或期望，可能包括但不限于性交易、利益交换等。\n4. **公众人物形象与隐私权**：涉及公众人物如何平衡个人隐私与公众关注之间的关系。\n5. **法律与道德**：探讨相关法律对性骚扰、职场不公等行为的界定及应对措施，以及社会对于这些行为的道德评价。\n6. **媒体责任与报道**：讨论媒体在报道此类敏感话题时的责任，包括信息来源的可信度、报道的公正性等。\n\n这些问题交织在一起，反映了娱乐圈内部的复杂生态和社会对于其长期关注的焦点。'}]
    output = judge_item("娱乐圈真的所有女艺人都被潜规则过吗？", "我不想看除机器学习以外的计算机相关的内容", histories)
    print(output)
    # response = get_bailian_response(histories)
    # # 先分析关联性, 在判断
    # print(f"********begin to print response********")
    # print(response)
    # print("********end to print response********")

    # # 提取结果, 理由， 规则
    # filter_result = False
    # filter_reason = ""
    # try:
    #     if response == "对不起，我无法帮助你":
    #         filter_reason = "DataInspectionFailed"
    #         filter_result = False
    #         print(filter_result, filter_reason)
    #     if len(response.split("\n")) < 2:
    #         response = response.strip()
    #         filter_result = True if response[0]=='是' else False
    #         filter_reason = response[2:]

    #     filter_result = True if "是" in response.split("\n")[0] else False
    #     filter_reason = '\n'.join(response.split("\n")[1:])
    # except:
    #     pass
    # print(filter_result, filter_reason)

