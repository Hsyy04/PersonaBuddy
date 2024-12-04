# 配置API

在 `agent\\prompt\\api.json` 配置

```json
{
    "bailian":{
        "api":"sk-xxx", //api
        "model": "qwen-turbo", 
        "dialog":"qwen-max"
    },
    "rah":{
        "update_interval_min": 15 //偏好更新时间间隔
    }
}
```

# 安装依赖
python 3.11以下
conda install pytorch==1.13.1 torchvision==0.14.1 torchaudio==0.13.1 cpuonly -c pytorch

requirements.txt是必须依赖的子集， requirements.txt.all是必需依赖的超集...  推荐：`pip install -r requirements.txt`


# 运行

记得迁移数据库！

1. python manage.py migrate
2. python manage.py runserver

更换数据库需要修改该settings

日志输出级别在 `PersonaBuddy/settings.py` 中修改
