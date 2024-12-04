import json
import random
import time
from .prompt.alignment import *
from .prompt.prompt_utils import get_bailian_response, extract_code_blocks
import os
import networkx as nx
from networkx.readwrite import json_graph
import numpy as np
from django.core import serializers
from django.forms.models import model_to_dict
import django
import logging
from .utils import get_edit_distance
logger = logging.getLogger("myapp")
from  retry import retry

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'PersonaBuddy.settings')
django.setup()
from .models import PersonalitiesClick


UPDATE_PROMPT = '''对于最接近的两个词语：“{old}”和“{new}”，请给出一个表意更加全面准确的名词短语，注意只输出最后的名词短语，不要输出任何额外的内容, 包括你的解释、标点'''
def rah_reflect_prompt(nodes, new_node):
    if len(nodes)==0:
        logger.warn("This is first node, no need to reflect")
        return None
    most_sim = -1
    min_distance = 10000000
    for exist_node in nodes:
        dist = get_edit_distance(exist_node, new_node) / float(max(len(exist_node), len(new_node)))
        if min_distance > dist:
            min_distance = dist
            most_sim = exist_node

    if min_distance>=0.3:
        return None
    if min_distance<=0.1:
        return most_sim, most_sim

    histories = [{"role": "user", "content": UPDATE_PROMPT.format(old=most_sim, new=new_node)}]
    logger.debug("******check rah reflect prompt********")
    logger.debug(histories)
    final_node = get_bailian_response(histories)
    logger.debug("******begin_reflect_prompt_response********")
    logger.debug(final_node)
    logger.debug("******end_reflect_prompt_response********")

    return most_sim, final_node.strip("\"")

@retry(tries=3, delay=1, backoff=2) # 把输出转化为图信息对精度要求太高了, 多试几次
def add_edge_w_update_node(graph, start, end, text2nodeid, nodeid2text, nodes, all_nodes_str):
    if start not in text2nodeid:
        reflect_res = rah_reflect_prompt(all_nodes_str, start)
        if reflect_res==None:
            nodes.append(start)
            text2nodeid[start] = len(nodes) - 1
            nodeid2text[len(nodes) - 1] = start
        else:
            old, new = reflect_res
            old_id = text2nodeid[old]
            nodes[old_id] = new
            text2nodeid[new] = old_id
            nodeid2text[old_id] = new
            start = new
    
    if end not in text2nodeid:
        reflect_res = rah_reflect_prompt(all_nodes_str, end)
        if reflect_res==None:
            nodes.append(end)
            text2nodeid[end] = len(nodes) - 1
            nodeid2text[len(nodes) - 1] = end
        else:
            old, new = reflect_res
            old_id = text2nodeid[old]
            nodes[old_id] = new
            text2nodeid[new] = old_id
            nodeid2text[old_id] = new
            end = new
    logger.info(f"start: {start}, end: {end}")

    if graph.has_edge(text2nodeid[start], text2nodeid[end]):
        graph[text2nodeid[start]][text2nodeid[end]]['weight'] += 1
    else:
        graph.add_edge(text2nodeid[start], text2nodeid[end], weight=1)

    return graph, nodes, text2nodeid, nodeid2text

def get_rah_personalities(pid, platform, pos_records, neg_records, sample_num=1, topK=10, bottomK=10):
    if not os.path.exists(f"agent/personalities/{pid}_{platform}.gml") or not os.path.exists(f"agent/personalities/{pid}_{platform}.json"):
        now_personalities = ""
        dislike_personalities = ""
    else:
        with open(f"agent/personalities/{pid}_{platform}.json", "r") as f:
            now_personalities = json.load(f)
            dislike_personalities = "\t".join(now_personalities[-min(len(now_personalities), bottomK):])
            now_personalities = "\t".join(now_personalities[:min(len(now_personalities),topK)])

    # # 先采样
    all_cands = []
    for click in pos_records:
        pos_reason = rah_summary_agent_pos(click, now_personalities, dislike_personalities)
        if len(pos_reason) == 0:
            continue
        negs = random.sample(neg_records, sample_num)
        for click_neg in negs:
            neg_reason = rah_summary_agent_neg(click_neg, now_personalities, dislike_personalities) 
            if len(pos_reason) == 0:
                continue
            candidates = rah_learn_agent(click, pos_reason, click_neg, neg_reason)
            all_cands.append(candidates)

    if not os.path.exists(f"agent/personalities/{pid}_{platform}.gml") or not os.path.exists(f"agent/personalities/{pid}_{platform}.json"):
        # 如果没有这个文件, 就新建一个
        nodes_set = set()
        nodes = list(nodes_set)
        g = nx.Graph()

        # save graph
        nx.write_gml(g, f"agent/personalities/{pid}_{platform}.gml")
    
        with open(f"agent/personalities/{pid}_{platform}.json", "w+") as f:
            json.dump(nodes, f, ensure_ascii=False)
    
    personalities_graph = nx.read_gml(f"agent/personalities/{pid}_{platform}.gml")
    with open(f"agent/personalities/{pid}_{platform}.json", "r") as f:
        nodes = json.load(f)

    text2nodeid = {text: i for i, text in enumerate(nodes)}
    nodeid2text = {i: text for i, text in enumerate(nodes)}
    for cand in all_cands:
        for edge in cand:
            nodes_str = "\t".join(nodes)
            start = edge[0]
            end = edge[1]
            #TODO: 添加不上边怎么办
            personalities_graph, nodes, text2nodeid, nodeid2text = add_edge_w_update_node(personalities_graph, start, end, text2nodeid, 
            nodeid2text, nodes, nodes_str)

    logger.debug(nodeid2text)
    logger.debug(personalities_graph)
    logger.debug(personalities_graph.edges())
    # save graph
    nx.write_gml(personalities_graph, f"agent/personalities/{pid}_{platform}.gml")
    with open(f"agent/personalities/{pid}_{platform}.json", "w+") as f:
        json.dump(nodes, f, ensure_ascii=False)

    # update personalities
    pagerank_scores = nx.pagerank(personalities_graph)
    sorted_pagerank = sorted(pagerank_scores.items(), key=lambda x: x[1], reverse=True)

    new_click = "\t".join([nodeid2text[i] for i, _ in sorted_pagerank[:min(topK, len(sorted_pagerank))]])
    logger.error(f"get new click personal:{new_click}")
    return new_click

if __name__=="__main__":
    import django
    from .utils import get_edit_distance
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'PersonaBuddy.settings')
    django.setup()

    clicks = ['当今科研圈，social不行是不是科研生涯也就到头了？', '电影《抓娃娃》表达了一个什么主题？']
    unclicks = ['泰森是要穷成什么样了，才会接叶问3这部戏，被Kungfu打一顿？', '为什么有的女生会看不起玩乙女向游戏的女生？', '如何评价二次元手游“有男不玩”？', '列举一些现在不知名，但在一个特定的时代全世界都知道的历史人物？', '周芷若一个船夫的女 儿，容貌真的比得上皇家女子吗？', '如果汉字失传了，释读它的难度有多大？', '中国算是世界上最安全的国家之一吗？', '香港艳星悲情史：情欲浮欢不作数，镜花水月已成空', '为什么格斗比赛中没见过铁山靠？', '为什么现在不创造新的汉字了？', '举办奥运会要烧多少钱？要是都亏，为啥各国都抢着做？']

    ret = get_rah_personalities("Hsyy06", "知乎", clicks, unclicks)
    print(ret)