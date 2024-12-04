from django.contrib import admin

from .models import * 


class RecordAdmin(admin.ModelAdmin):
    list_display = ('pid', 'title', 'filter_result', 'browse_time', 'click', 'click_time','is_filter', 'filter_reason')
    list_filter = ['pid', 'filter_result', 'click', 'browse_time', 'click_time']
    search_fields = ['title', 'content', 'context', 'filter_reason']
    fieldsets = [
        ('交互信息', {'fields': ['pid', 'title', 'content', 'click']}),
        ('上下文信息', {'fields': ['context', 'filter_result', 'filter_reason']})
    ]


class RuleAdmin(admin.ModelAdmin):
    list_display = ('iid', 'pid', 'rule', 'isactive')
    list_filter = ['iid', 'pid', 'isactive']
    search_fields = ['rule']

class SessionAdmin(admin.ModelAdmin):
    def chat_history(self, obj):
        return obj.message_set.all()
    chat_history.short_description = '聊天记录'

    list_display = ('pid', 'task', 'summary','chat_history')
    list_filter = ['pid', 'task']
    search_fields = ['summary']

# class MessageAdmin(admin.ModelAdmin):
#     list_display = ('session', 'content', 'sender', 'has_action')
#     list_filter = ['session', 'sender', 'has_action']
#     search_fields = ['content', 'sender']

class ChilogAdmin(admin.ModelAdmin):
    list_display = ('pid', 'iid', 'action_type', "isbot", "rule")
    list_filter = ['pid', 'iid', 'action_type', "isbot"]
    search_fields = ['pid', 'iid', 'action_type','rule']

class GenContentlogAdmin(admin.ModelAdmin):
    list_display = ('pid', 'action_type','new_rule', 'is_ac', "old_rule", "change_rule")
    list_filter = ['pid', 'action_type','is_ac']
    search_fields = ['new_rule','old_rule', "change_rule"]

class SearchlogAdmin(admin.ModelAdmin):
    list_display = ('pid', 'gen_keyword','edited_keyword', 'is_accepted')
    list_filter = ['pid', 'is_accepted']
    search_fields = ['gen_keyword','edited_keyword']

class PersonalitiesAdmin(admin.ModelAdmin):
    list_display = ('pid', 'personality','personality_click', 'first_response')
    list_filter = ['pid',]
    search_fields = ['personality','personality_click', 'first_response']


admin.site.register(Record, RecordAdmin)
admin.site.register(Rule, RuleAdmin)
admin.site.register(Session, SessionAdmin)
admin.site.register(Message)
admin.site.register(Chilog, ChilogAdmin)
admin.site.register(GenContentlog, GenContentlogAdmin)
# admin.site.register(Searchlog, SearchlogAdmin)
admin.site.register(Personalities, PersonalitiesAdmin)
admin.site.register(PersonalitiesClick)
