from django.urls import path

from .views import *

urlpatterns = [
    path("browse", browse),
    path("click", click),
    path("chatbot", dialogue),
    path("chatbot/report", report),
    path("chatbot/get_sessions", get_sessions),
    path("save_rules", save_rules),
    path("chatbot/get_history/<int:sid>", get_history),
    path("get_alignment", get_alignment),
    path("get_feedback", get_feedback),
    path("save_search", save_search),
    path("make_new_message", make_new_message),
    path("get_word_count", get_word_count), # 这个是作词云用的,现在废弃了
    path("record_user", record_user),
]
