SUCCESS = 0
FAILURE = -1
PLATFORM_CHOICES = [
    ('知乎', '知乎'),
    ('B站', 'B站'),
    ('小红书', '小红书'),
    ('微博', '微博'),
]
PLATFORMS=[item[0] for item in PLATFORM_CHOICES]

TASK_CHOICES = [
    ("0","变更画像"),
    ("1","对齐画像"),
    ("2", "查看留痕")
]
