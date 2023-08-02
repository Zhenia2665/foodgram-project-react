## Описание 
Проект Foodgram – это блог, где авторизированные юзеры могут публиковать свои рецепты, подписываться на других пользователей, добавлять рецепты в список «Избранное», а также скачивать список продуктов, которые нужны для приготовления выбранных рецептов. Для неавторизированных юзеров доступен только просмотр рецептов.  
 
## Стек проекта: 
 
- Python 
- Django 
- DRF 
- Docker 
- Gunicorn 
- Nginx 
- PostresSQL 
 
## Запуск проекта на сервере: 
 
Установить на сервере docker и docker-compose. Скопировать на сервер файлы docker-compose.yaml и default.conf: 
 
 
scp docker-compose.yml <логин_на_сервере>@<IP_сервера>:/home/<логин_на_сервере>/docker-compose.yml 
scp nginx.conf <логин_на_сервере>@<IP_сервера>:/home/<логин_на_сервере>/nginx.conf 
 
 
 
Добавить в секреты на гитхабе следующие данные: 
 
 
DB_ENGINE=django.db.backends.postgresql 
DB_NAME=postgres 
POSTGRES_USER=postgres 
POSTGRES_PASSWORD=postgres 
DB_HOST=db 
DB_PORT=5432 
SECRET_KEY='Здесь указать секретный ключ' 
ALLOWED_HOSTS='Здесь указать имя или IP хоста' (Для локального запуска - 127.0.0.1) 
 
 
 
В директории infra в терминале ввести команду: 
docker-compose up 
sudo docker-compose exec web python manage.py migrate 
sudo docker-compose exec web python manage.py collectstatic --no-input  
 
 
После этого нужно создать суперпользователя и загрузить в админке информацию об ингредиентах: 
 
 
sudo docker-compose exec web python manage.py createsuperuser 
 
 
## Запуск проект локально: 
 
Клонировать репозиторий и перейти в него в командной строке: 
 
 git@github.com:Zhenia2665/foodgram-project-react.git```  
 cd foodgram-project-react   
 
Создать и активировать виртуальное окружение: 
 
 python3 -m venv venv   
 
* Если у вас Linux/macOS: 
     source venv/bin/activate   
 
* Если у вас Windows: 
     source venv/Scripts/activate  
     
 python3 -m pip install --upgrade pip   
 
Установить зависимости из файла requirements: 
 
 pip install -r requirements.txt   
 
Выполнить миграции: 
 
 python3 manage.py migrate   
 
Запустить проект: 
 
 python3 manage.py runserver   
 
 
## Автор проекта 
Тарасова docker Евгения. 
admin@mail.ru 
admin 
ip: 84.201.143.93