import json
import re
import random
import time
from .prompt_utils import get_bailian_response, get_common_response, extract_code_blocks
import logging
logger = logging.getLogger("myapp")
from django.conf import settings


CLICKS_PROMPT ='''请根据[用户点击内容]，分析用户对推荐系统改的个性化需求, 你需要给出几个短语总结个性化偏好.

**用户点击内容**:
{clicks}

注意, 你的回答应该尽可能简短, 不要过度解释, 也不要输出额外的内容.''' 
def get_simple_personalities_from_clicks(clicks):
    clicks_str = "\n".join(clicks)
    # 通过点击内容和过滤规则总结用户偏好
    logger.debug("******check alignment prompt********")
    logger.debug(CLICKS_PROMPT.format(clicks=clicks_str))
    clicks = "\n".join(clicks)
    response = get_bailian_response([{"role": "user", "content": CLICKS_PROMPT.format(clicks=clicks)}])
    return response


ANALYZE_PROMP ='''请根据[用户浏览内容]，分析用户对推荐系统改的个性化需求, 你需要给出几个短语总结个性化偏好.

**用户浏览内容**:
{browses}

注意, 你的回答应该尽可能简短, 不要过度解释, 也不要输出额外的内容.''' 
def get_simple_personalities_from_browses(browses):
    browses_str = "\n".join(browses)
    # 通过点击内容和过滤规则总结用户偏好
    logger.debug("******check alignment prompt********")
    logger.debug(ANALYZE_PROMP.format(browses=browses_str))
    response = get_bailian_response([{"role": "user", "content": ANALYZE_PROMP.format(browses=browses_str)}])
    logger.debug("********begin to print response********")
    logger.debug(response)
    logger.debug("********end to print response********")
    return response
        

## RAH! summary agent
ADD_PROMP = '''假如你是一个在线问答平台的用户，你对这些内容感兴趣：
{personallities}
对这些内容不感兴趣：
{dislike}'''
SUMMMARY_PROMPT_RAH = '''现在，我观察到你点击了标题为“{title}”的内容，请你以**第一人称**解释一下原因。

请你以json格式回复，严格按照以下格式返回结果：
{{
    "answer": "<点击的原因（第一人称）>"
}}'''
def rah_summary_agent_pos(title, personalities="", dislikes=""):

    template = ADD_PROMP+SUMMMARY_PROMPT_RAH if (len(personalities)>0 and len(dislikes)>0) else SUMMMARY_PROMPT_RAH
    logger.debug("******check rah summary prompt********")
    logger.debug([{"role": "user", "content": template.format(personallities=personalities, dislike=dislikes, title=title)}])
    response = get_bailian_response([{"role": "user", "content": template.format(personallities=personalities, dislike=dislikes, title=title)}])
    logger.debug("******begin_pos_summary_response********")
    logger.debug(response)
    logger.debug("******end_pos_summary_response********")

    try:
        if response.startswith("```"):
            response = extract_code_blocks(response, "json")
        res = json.loads(response)
        answer = res['answer']
        return answer
    except:
        logger.error(f"总结pos原因的agent没有正常返回 {response}")
        return ""

ADD_PROMP_N = '''假如你是一个在线问答平台的用户，你对这些内容感兴趣：
{personallities}
对这些内容不感兴趣：
{dislike}'''
SUMMMARY_PROMPT_RAH_N = '''现在，我观察到没有点击标题为“{title}”的内容，请你以**第一人称**解释一下原因。


请你以json格式回复，严格按照以下格式返回结果：
{{
    "answer": "<没点击的原因（第一人称）>"
}}'''
def rah_summary_agent_neg(title, personalities="", dislikes=""):

    template = ADD_PROMP_N+SUMMMARY_PROMPT_RAH_N if (len(personalities)>0 and len(dislikes)>0) else SUMMMARY_PROMPT_RAH_N
    logger.debug("******check rah summary prompt********")
    logger.debug([{"role": "user", "content": template.format(personallities=personalities, dislike=dislikes, title=title)}])
    response = get_bailian_response([{"role": "user", "content": template.format(personallities=personalities, title=title, dislike=dislikes)}])
    logger.debug("******begin_neg_summary_response********")
    logger.debug(response)
    logger.debug("******end_neg_summary_response********")
    try:
        if response.startswith("```"):
            response = extract_code_blocks(response, "json")
        res = json.loads(response)
        answer = res['answer']
        return answer
    except:
        logger.error(f"总结neg原因的agent没有正常返回 {response}")
        return ""


LEARNT_PROMPT = '''一个在线问答平台的用户点击了标题为“{title}”的内容，他给出的原因是“{reason}”

现在请你从原因中总结两个名词短语，能够概括该用户对什么内容感兴趣，且这两个名词短语应该描述了不同的方面。


请你以json格式回复，严格按照以下格式返回结果：
{{
    "answer": ["<名词短语1>", "<名词短语2>"]
}}
'''
def rah_learn_agent_pos(title, reason):
    logger.debug("******check rah learn prompt********")
    logger.debug(LEARNT_PROMPT.format(title=title, reason=reason))
    response = get_bailian_response([{"role": "user", "content": LEARNT_PROMPT.format(title=title, reason=reason)}])
    logger.debug("******begin_learn_prompt_response********")
    logger.debug(response)
    logger.debug("******end_learn_prompt_response********")

    # 这里分析出来的是喜欢的特征
    try:
        if response.startswith("```"):
            response = extract_code_blocks(response, "json")
        res = json.loads(response)
        answer = res['answer']
        return answer
    except:
        logger.error(f"分析pos特征的agent没有正常返回{response}")
        return []

LEARNT_PROMPT_N = '''一个在线问答平台的用户没有点击标题为“{title}”的内容，他给出的原因是“{reason}”

现在请你从原因中总结两个名词短语，能够概括该用户对什么内容不感兴趣，且这两个名词短语应该描述了不同的方面。


请你以json格式回复，严格按照以下格式返回结果：
{{
    "answer": ["<名词短语1>", "<名词短语2>"]
}}
'''
def rah_learn_agent_neg(title, reason):
    logger.debug("******check rah learn prompt********")
    logger.debug(LEARNT_PROMPT_N.format(title=title, reason=reason))
    response = get_bailian_response([{"role": "user", "content": LEARNT_PROMPT.format(title=title, reason=reason)}])
    logger.debug("******begin_learn_prompt_response********")
    logger.debug(response)
    logger.debug("******end_learn_prompt_response********")

    # 这里分析出来的试不喜欢的特征
    try:
        if response.startswith("```"):
            response = extract_code_blocks(response, "json")
        res = json.loads(response)
        answer = res['answer']
        return answer
    except:
        logger.error(f"分析neg特征的agent没有正常返回{response}")
        return []

def rah_learn_agent(pos_title, pos_reson, neg_title, neg_reason):
    pos_res = rah_learn_agent_pos(pos_title, pos_reson)
    neg_res = rah_learn_agent_neg(neg_title, neg_reason)
    
    ret_edges = []
    for pos in pos_res:
        for neg in neg_res:
            ret_edges.append((pos, neg))

    return ret_edges


