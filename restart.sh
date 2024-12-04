python manage.py flush
rm -rf agent/personalities/*.*
rm -rf django_debug.log
python manage.py createsuperuser
python manage.py runserver