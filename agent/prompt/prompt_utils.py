import json
import re
import time
from http import HTTPStatus
import dashscope
import logging
logger = logging.getLogger("myapp")

with open("agent/prompt/api.json","r") as f:
    settings_file = json.load(f)

API = settings_file["bailian"]['api']
MODEL = settings_file["bailian"]['model']
DIALOG_MODEL = settings_file["bailian"]['dialog']
dashscope.api_key = API

interval = settings_file["rah"]['update_interval_min']

def extract_code_blocks(markdown_text, language):
    # 定义正则表达式模式
    pattern = rf'```{language}\n(.*?)\n```'
    
    # 使用 re.DOTALL 使 . 匹配换行符
    code_blocks = re.findall(pattern, markdown_text, re.DOTALL)
    
    return code_blocks[0]

def get_bailian_response(msg, model=MODEL):
    init_prompt  = [{"role":"system","content":"你是一个非常聪明有用的客服"}]
    msg = init_prompt + msg
    response = dashscope.Generation.call(model, messages=msg)
    cnt_try = 0
    while response["status_code"] != HTTPStatus.OK and cnt_try < 2:
        time.sleep(1)
        
        logger.error('Request id: %s, Status code: %s, error code: %s, error message: %s' % (
                response.request_id, response.status_code,
                response.code, response.message
        ))
        response = dashscope.Generation.call(model, messages=msg)
        cnt_try+=1
    if response["status_code"] != HTTPStatus.OK:
        return "对不起，我无法帮助你"
    return response['output']['text']


REPONSE = """你的目标是探索用户在社交媒体中的个性化需求, 也就是他们更不愿意看到什么内容, 请根据上下文给出恰当的回复. 请记住, 你的回复应该尽可能简短, 通过询问用户更多信息来鼓励user表达需求.

**聊天上下文**:
{messages}
客服："""
def get_common_response(messages):
    print("******check common response prompt********")
    print(REPONSE.format(messages=messages))
    response = get_bailian_response([{"role": "user", "content":REPONSE.format(messages=messages)}])
    print(response)
    return response

def get_clean_items(items):
    '''
        items: list, 待清洗的内容
    '''
    ret_items = []
    for item in items:
        if item.strip() == "": continue
        item = item.strip()
        # 删除数字之前的东西
        index = re.search(r"\d", item)
        if index is not None:
            item = item[index.start():]

        # 提取 数字. 之后的文本
        item = re.sub(r'^\d+\.\s*', '', item)

        ret_items.append(item)
    return ret_items
