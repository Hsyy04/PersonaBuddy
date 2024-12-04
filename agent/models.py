from django.db import models
from .const import PLATFORM_CHOICES
from .const import TASK_CHOICES


class Record(models.Model):

    pid = models.CharField(max_length=10, default="", verbose_name='参与者')
    platform = models.CharField(max_length=10, choices=PLATFORM_CHOICES, default='知乎', verbose_name='平台')
    title = models.CharField(max_length=200, default="", verbose_name='标题')
    content = models.CharField(max_length=1000, default="", verbose_name='内容') #TODO:感觉获取全文很难, 而且B站可是视频啊,先不考虑了
    url = models.CharField(max_length=1000, default="", verbose_name='网址')
    click = models.BooleanField(default=False, verbose_name='点击')
    browse_time = models.DateTimeField(auto_now_add=True, verbose_name='浏览时间')
    click_time = models.DateTimeField(auto_now=True, verbose_name='交互时间')
    context = models.CharField(max_length=1000, default="", verbose_name='对应规则') # 导致过滤的那条rule
    is_filter = models.BooleanField(default=True, verbose_name='开关')
    filter_result = models.BooleanField(default=False, verbose_name='屏蔽')
    filter_reason = models.CharField(max_length=2000, default="", verbose_name='原因')
    sum_content = models.CharField(max_length=1000, default="", verbose_name='摘要') # 用于rah的建模cache

    class Meta:
        verbose_name = '记录'
        verbose_name_plural = '记录'
        indexes = [
            models.Index(fields=['pid']),
            models.Index(fields=['platform']),
            models.Index(fields=['pid', 'platform']),
            models.Index(fields=['pid', 'platform', 'title']),
        ]

    def __str__(self):
        return f"{self.pid} - {self.title[:100]}{'...' if len(self.title) > 100 else ''}"


class Rule(models.Model):
    iid = models.IntegerField(default=-1, verbose_name='规则编号')
    pid = models.CharField(max_length=10, default="P00", verbose_name='参与者')
    rule = models.CharField(max_length=100, verbose_name='规则')
    isactive = models.BooleanField(default=True, verbose_name='激活')
    platform = models.CharField(max_length=10, choices=PLATFORM_CHOICES, default='知乎', verbose_name='平台')

    class Meta:
        verbose_name = '规则'
        verbose_name_plural = '规则'
        indexes = [
            models.Index(fields=['pid']),
        ]

    def __str__(self):
        return f"{self.iid} - {self.rule}"


class Session(models.Model):
    pid = models.CharField(max_length=10, default="P00", verbose_name='参与者')
    task = models.CharField(max_length=100, choices=[], verbose_name='任务', default="无")
    platform = models.CharField(max_length=10, choices=PLATFORM_CHOICES, default='知乎', verbose_name='平台')
    summary = models.CharField(max_length=100, default="", verbose_name='总结')

    class Meta:
        verbose_name = '会话'
        verbose_name_plural = '会话'
        indexes = [
            models.Index(fields=['pid']),
        ]

class Message(models.Model):
    session = models.ForeignKey(Session, on_delete=models.CASCADE)
    content = models.CharField(max_length=255, verbose_name="内容")
    sender = models.CharField(max_length=10, choices=[("user", "user"), ("assistant", "assistant"),("bot","bot")], default="bot", verbose_name="发送者")  
    has_action = models.BooleanField(default=False) # 用来切割上下文的，如果用户ac了一些action，那么就是True， 意味着后面的上下文不要过于关注探索上一个action的utterance
    timestamp = models.DateTimeField(auto_now_add=True)
    # has_acc_action = models.BooleanField(default=False) # 这个消息对应的操作是否被接受了

    class Meta:
        verbose_name = '消息'
        verbose_name_plural = '消息'


    def __str__(self):
        return f"{self.sender}-{self.content}"
    
class Chilog(models.Model): # 每次一对规则的操作都要记录
    pid = models.CharField(max_length=10, default="P00", verbose_name='参与者')
    iid = models.IntegerField(default=-1, verbose_name='规则编号')
    action_type = models.CharField(max_length=10, choices=[("add", "add"), ("update", "update"), ('delete','delete')], default="add", verbose_name='操作类型')
    isbot =models.BooleanField(default=False, verbose_name='是否是通过bot操作')# 如果通过直接管理就是False
    rule = models.CharField(max_length=100, verbose_name='改变后的规则', null=True) # 如果是删除就没有
    isactive = models.BooleanField(default=True, verbose_name='改变后的激活', null=True)
    platform = models.CharField(max_length=10, choices=PLATFORM_CHOICES, default='知乎', verbose_name='改变后的平台', null=True)
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name='时间')
    
    class Meta:
        verbose_name = '规则编辑日志'
        verbose_name_plural = '规则编辑日志'

class GenContentlog(models.Model):
    pid = models.CharField(max_length=10, default="P00", verbose_name='参与者')
    action_type = models.CharField(max_length=10, choices=[("add", "add"), ("update", "update"), ('delete','delete')], default="add", verbose_name='操作类型')
    platform = models.CharField(max_length=10, choices=PLATFORM_CHOICES, default='知乎', verbose_name='平台')
    new_rule = models.CharField(max_length=100, verbose_name='生成规则') 
    old_rule = models.CharField(max_length=100, verbose_name='原规则')
    is_ac = models.BooleanField(default=True, verbose_name='是否被接受')
    change_rule = models.CharField(max_length=100, verbose_name='用户编辑后的规则') 
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name='时间')
    from_which_session = models.ForeignKey(Session, on_delete=models.CASCADE, null=True)
    from_which_message = models.ForeignKey(Message, on_delete=models.CASCADE, null=True)

    class Meta:
        verbose_name = '规则生成日志'
        verbose_name_plural = '规则生成日志'
    
class Searchlog(models.Model):
    pid = models.CharField(max_length=10, default="P00", verbose_name='参与者')
    platform = models.CharField(max_length=10, choices=PLATFORM_CHOICES, default='知乎', verbose_name='平台')
    gen_keyword = models.CharField(max_length=100, default="", verbose_name='关键词')
    edited_keyword = models.CharField(max_length=100, default="", verbose_name='用户编辑后的关键词')
    is_accepted = models.BooleanField(default=False, verbose_name='是否被接受')
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name='时间')
    class Meta:
        verbose_name = '搜索日志'
        verbose_name_plural = '搜索日志'

class Personalities(models.Model):
    pid = models.CharField(max_length=10, default="P00", verbose_name='参与者')
    platform = models.CharField(max_length=10, choices=PLATFORM_CHOICES, default='知乎', verbose_name='平台')
    personality = models.CharField(max_length=500, default="", verbose_name='个性化偏好')
    personality_click = models.CharField(max_length=500, default="", verbose_name='点击偏好')
    first_response = models.CharField(max_length=500, default="", verbose_name='第一句回答')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '个性化偏好'
        verbose_name_plural = '个性化偏好'

    def __str__(self) -> str:
        return f"{self.personality_click} - {self.personality}"
    
class PersonalitiesClick(models.Model):
    pid = models.CharField(max_length=10, default="P00", verbose_name='参与者')
    platform = models.CharField(max_length=10, choices=PLATFORM_CHOICES, default='知乎', verbose_name='平台')
    personality_click = models.CharField(max_length=500, default="", verbose_name='点击偏好')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = 'RAH生成的点击偏好'
        verbose_name_plural = 'RAH生成的点击偏好'
    def __str__(self) -> str:
        return f"{self.personality_click}"

class UserPid(models.Model):
    pid = models.CharField(max_length=10, default="P00", verbose_name='参与者')
    def __str__(self) -> str:
        return f"{self.pid}"
