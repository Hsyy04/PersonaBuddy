import json
import re
from .prompt_utils import get_bailian_response, get_common_response

NEED_FEEDBACK_PROMPT='''请根据[聊天上下文]判断: 用户是否要求查看*过滤历史*以及*搜索历史*. 如果是, 请判断需要查看多少条, 如果判断不出来个数, 默认为10条. 

**聊天上下文**:
{messages}

回答格式应该是一个json字段包含以下内容:
- need_check_filter: int, 需要查看过滤历史的条数
- need_check_search: int, 需要查看搜索历史的条数

示例:
聊天上下文: "用户:你好"
回答:{{'need_check_filter': 0, 'need_check_search': 0}}
聊天上下文: "用户:你好\n客服:你好, 有什么可以帮助你的?\n用户:我想知道你到底过滤了什么?"
回答:{{'need_check_filter': 10, 'need_check_search': 0}}
'''


def check_is_need_feedback(chat_history):
    '''
        chat_history: "user:xxx\nassistant:xxx\nuser:xxx\n..."

        返回: (need_check_filter, need_check_search)
    '''
    print("******check is need feedback prompt********")
    print(NEED_FEEDBACK_PROMPT.format(messages=chat_history))
    need_feedback = get_bailian_response([{"role": "user", "content": NEED_FEEDBACK_PROMPT.format(messages=chat_history)}])
    print(need_feedback)
    try:
        need_feedback = json.loads(need_feedback)
        return need_feedback['need_check_filter'], need_feedback['need_check_search']
    except:
        return False, False