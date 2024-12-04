from django.http import JsonResponse
from .models import * 
import random
from .prompt.filter import filter_item
from .prompt.fuzzy import get_fuzzy
from .prompt.alignment import get_simple_personalities_from_browses, get_simple_personalities_from_clicks
from .prompt.prompt_utils import get_common_response
from .prompt.feedback import check_is_need_feedback

import jieba
import collections

from django.conf import settings

def build_response(code, data):
    response = JsonResponse({'code': code, 'data': data})
    response['Access-Control-Allow-Origin'] = '*'
    return response

def check_filter(pid, platform, count=10):
    filter_history = Record.objects.filter(pid=pid, platform=platform, filter_result=True, is_filter=True).order_by('-browse_time')
    count = min(count, len(filter_history))
    filter_history = filter_history[:count]
    filter_titles = [(record.title, record.filter_reason, record.context) for record in filter_history]
    # suggest_search = [search.keyword for search in search_history]
    return filter_titles


def check_search(pid, platform, count=10):
    search_history = Searchlog.objects.filter(pid=pid, platform=platform).order_by("-timestamp")
    count = min(count, len(search_history))
    search_history = search_history[:count]
    accepted_search = [search.keyword for search in search_history if search.is_accepted] #TODO: 这里可以返回关联规则.
    return accepted_search


def feedback_to_response(pid, platform, count=10):
    response = ""
    filter_titles = check_filter(pid, platform)
    if len(filter_titles) == 0:
        response += f"我最近没有过滤任何内容\n\n"
    else:
        response += f"我最近过滤了如下内容:\n"
        goup_by_rule = {}
        for title, reason, rule in filter_titles:
            if rule not in goup_by_rule:
                goup_by_rule[rule] = []
            goup_by_rule[rule].append((title, reason))

        for rule in goup_by_rule:
            response += f"* 基于规则 *{rule}* 过滤了如下内容: \n\n"
            for title, reason in goup_by_rule[rule]:
                response += f"\t标题: **{title}**\n\n"
        response+="\n"

    # search_titles = check_search(pid, platform)
    # if len(search_titles) == 0:
    #     response += f"我最近没有搜索任何内容\n\n"
    # else:
    #     search_str = "\n".join(search_titles)
    #     response += f"通过聊天出发了以下关键词的搜索: \n{search_str}\n\n"
    
    response += "请问有什么疑问吗?"
    return response

def get_his_message_str(sid):
    def get_tem_history(sid):
        messages = Message.objects.filter(session=sid).order_by('timestamp')
        return [{'role': message.sender, 'content': message.content} for message in messages]
    # 获取历史
    messages = get_tem_history(sid)
    message_obj = Message.objects.filter(session=sid).order_by('timestamp')
    start_id = 0
    for i in reversed(range(len(message_obj))):
        if message_obj[i].has_action:
            start_id = i
            break
    messges_str = ""
    if start_id!=0 and messages[0]['role'] == 'bot':
        messges_str = f"客服:{messages[0]['content']}\n"
        start_id+=1
    messges_str += "\n".join([f"{'用户' if m['role']=='user' else '客服'}: {m['content']}" for m in messages[start_id:]])
    print(messges_str)
    return messges_str


with open(f"{settings.BASE_DIR}/agent/stopwords.txt", 'r', encoding='utf-8') as f:
    stopwords = [line.strip() for line in f.readlines()]
def get_browses_wc(pid, platform, count=10):
    browses = Record.objects.filter(pid=pid, platform=platform, is_filter=True).order_by('-browse_time')
    browse_titles = [browse.title for browse in browses[:min(count, len(browses))]]

    # 分词并聚合
    all_words = []
    for title in browse_titles:
        all_words += jieba.cut(title)
    word_count = collections.Counter(all_words)
    # delete stopwords
    for word in list(word_count.keys()):
        if word in stopwords:
            del word_count[word]
    return word_count

def get_clicks_wc(pid, platform, count=10):
    clicks = Record.objects.filter(pid=pid, platform=platform, click=True, is_filter=True).order_by('-browse_time')
    click_titles = [click.title for click in clicks[:min(count, len(clicks))]]

    # 分词并聚合
    all_words = []
    for title in click_titles:
        all_words += jieba.cut(title)
    word_count = collections.Counter(all_words)
    # delete stopwords
    for word in list(word_count.keys()):
        if word in stopwords:
            del word_count[word]
    return word_count

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