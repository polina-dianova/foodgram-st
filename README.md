«Фудграм» — сайт, на котором пользователи будут публиковать свои рецепты, добавлять чужие рецепты в избранное и подписываться на публикации других авторов. Зарегистрированным пользователям также будет доступен сервис «Список покупок». Он позволит создавать список продуктов, которые нужно купить для приготовления выбранных блюд.

## Запуск проекта

1. Клонируйте репозиторий
```bash
git clone https://github.com/polina-dianova/foodgram-st.git
```

2. Перейдите в директорию `infra` и создайте файл `.env` в директории `infra` на основе `.env.example`:
```bash
cd foodgram-st/infra
```
```bash
touch .env
```

3. В директории `infra` Запустите проект:
```bash
docker-compose up 
```

4. Выполните миграции:
```bash
docker-compose exec backend python manage.py migrate
```

5. Заполните базу ингредиентами и тестовыми данными:
```bash
docker-compose exec backend python manage.py load_ingredients
```

## Адреса

- Веб-интерфейс: [Localhost](http://localhost/)
- API документация: [Localhost docs](http://localhost/api/docs/)
- Админ-панель: [Localhost admin](http://localhost/admin/)
