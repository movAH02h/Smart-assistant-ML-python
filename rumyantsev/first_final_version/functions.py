# Сделать так чтобы голосовой помощник отвечал без имени на обычные фразы, а на active только с именем
import os.path
from fuzzywuzzy import fuzz
import pyowm
import numpy as np
import sys
from pycbrf import ExchangeRates
from pyowm.utils.config import get_default_config
import random
import queue
import sounddevice as sd
import vosk
import locale
import pyttsx3
import json
import datetime
from new_version import data_set
import time
import wikipediaapi
import urllib.parse
from bs4 import BeautifulSoup
from googletrans import Translator
import webbrowser
import requests
from tensorflow import keras
import smtplib
from email.mime.text import MIMEText
from email.header import Header

class NotFoundException(Exception):
    pass

q = queue.Queue()
model = vosk.Model('../model_small')
device = sd.default.device
samplerate = int(sd.query_devices(device[0], 'input')['default_samplerate'])

def search_google(text=""):
    if text == "":
        user_query = listen()
    else:
        user_query = text

    encoded_query = urllib.parse.quote(user_query)
    webbrowser.open_new_tab(f"https://www.google.com/search?q={encoded_query}")
    # Ждем несколько секунд для загрузки страницы
    time.sleep(3)
    # Получаем HTML-код страницы результатов поиска
    search_results_page = requests.get(f"https://www.google.com/search?q={encoded_query}")
    soup = BeautifulSoup(search_results_page.content, 'html.parser')
    # Ищем все заголовки и ссылки на странице результатов
    titles = soup.find_all('h3')
    links = soup.find_all('a')
    # Выводим название сайта и URL первых трех ссылок
    for title, link in zip(titles[:3], links[:3]):
        link_text = title.text
        # link_url = link.get('href')
        # Получаем доменное имя из URL
        # domain = re.findall(r'https?://(?:www\.)?(.*?)/', link_url)[0]
        print(f"{link_text}")

    say("Вот, что мне удалось найти по вашему запросу.")

def help():
    with open("abilities.txt", "r", encoding='utf-8') as file:
        information = file.readlines()

    for lines in information:
        print(lines)


def checking_time():
    current_time = datetime.datetime.now().strftime("%H:%M")
    print(f"Сейчас {current_time}")
    say(f"Сейчас {current_time}")

def current_date():
    locale.setlocale(locale.LC_TIME, 'ru')  # Установка локали для вывода на русском языке
    date = datetime.datetime.now()
    day_of_week = date.strftime("%A")
    day = date.day
    month = date.strftime("%B")  # Форматируем месяц с большой буквы
    year = date.year

    say(f"Сегодня {day_of_week}, {day} {month} {year} года.")

def translate_to_english():
    text = listen()

    translator = Translator()
    try:
        translation = translator.translate(text, dest='en', src='ru')
        print(translation.text)
        say(f"перевод звучит так: {translation.text}")
    except AttributeError:
        say("ошибка распознавания. попробуйте еще раз")

def search_recipe():
    def russian_to_english(text):
        translator = Translator()
        try:
            translation = translator.translate(text, dest='en', src='ru')
            return translation.text
        except AttributeError:
            return -1

    def english_to_russian(text):
        translator = Translator()
        try:
            translation = translator.translate(text, dest='ru', src='en')
            return translation.text
        except AttributeError:
            return -1
    """
    Поиск рецепта по запросу пользователя с помощью API The Meal DB
    """
    query = listen()

    translated_query = russian_to_english(query)
    if (translated_query == -1):
        say("небольшая ошибочка попробуйте еще раз пожалуйста")
        return

    print(translated_query)

    url = f"https://www.themealdb.com/api/json/v1/1/search.php?s={translated_query}"
    response = requests.get(url)
    data = response.json()

    if data['meals']:
        meal = data['meals'][0]
        recipe_name = english_to_russian(meal['strMeal'])
        ingredients = []
        for i in range(1, 21):
            ingredient = meal.get(f'strIngredient{i}')
            if ingredient:
                ingredients.append(english_to_russian(ingredient))
            else:
                break

        instructions = english_to_russian(meal['strInstructions'])

        recipe_text = f"Рецепт блюда {recipe_name}:"
        recipe_text += "\n\nИнгредиенты:"
        for ingredient in ingredients:
            recipe_text += f"\n- {ingredient}"
        recipe_text += f"\n\nИнструкции по приготовлению:\n{instructions}"

        print(recipe_text)
    else:
        say("к сожалению в моей базе данных нет такого рецепта. Вот результаты поиска в гугл. Может вам пригодится")
        search_google(query)

def search_youtube():
    user_query = listen()

    encoded_query = urllib.parse.quote(user_query)
    webbrowser.open_new_tab(f"https://www.youtube.com/results?search_query={encoded_query}")


def to_do_list_create():
    desktop_file = os.path.join(os.path.join(os.environ['USERPROFILE']), 'Desktop' + "\\" + "to_do_list.txt")
    if (os.path.exists(desktop_file)):
        say("такой список уже есть")
    else:
        file = open(desktop_file, "w", encoding='utf-8')
        file.close()
        say("создан список задач")

def to_do_list_add():
    desktop_file = os.path.join(os.path.join(os.environ['USERPROFILE']), 'Desktop' + "\\" + "to_do_list.txt")
    try:
        data = listen()
        file = open(desktop_file, "a+", encoding='utf8')
        file.write(data + "\n")
        file.close()
        say(f"Задача '{data}' добавлена в список дел.")
    except FileExistsError:
        say("Список задач для начала нужно создать. Для этого скажите кеша создай список задач")

def to_do_list_show():
    desktop_file = os.path.join(os.path.join(os.environ['USERPROFILE']), 'Desktop' + "\\" + "to_do_list.txt")
    try:
        file = open(desktop_file, "r", encoding='utf-8')
        content = file.readlines()
        for line in content:
            say(line)
        file.close()
    except FileExistsError:
        print("no")
        say("Список задач не создан")

def to_do_list_remove():
    desktop_file = os.path.join(os.path.join(os.environ['USERPROFILE']), 'Desktop' + "\\" + "to_do_list.txt")
    try:
        task = listen()
        file = open(desktop_file, "r+", encoding='utf-8')
        content = list(file.readlines())
        print(content)
        total_rate, line = 0, ""
        for element in content:
            current_rate = fuzz.ratio(element, task)
            if (current_rate > total_rate):
                total_rate = current_rate
                line = element

        print(line)

        content.remove(line)
        file.seek(0)

        for element in content:
            file.write(element)

        #усечение файла до текущей позиции курсора (чтобы полностью перезаписать файл)
        file.truncate()

        file.close()
    except FileExistsError:
        say("сначала надо создать файл с задачами")

def send_message_to_all():
    mail = 'KARum2004@yandex.ru'
    message = listen()

    password = ''
    with open("new_project/source.txt", 'r', encoding='utf-8') as file:
        password = file.readline()

    msg = MIMEText(f'{message}', 'plain', 'utf-8')
    msg['Subject'] = Header('От голосового помощника Кеши', 'utf-8')
    msg['From'] = mail

    server = smtplib.SMTP('smtp.yandex.ru', 587, timeout=10)

    try:
        server.starttls()
        server.login(mail, password)
        for other_mail in data_set.posts.values():
            msg['To'] = other_mail
            server.sendmail(msg['From'], other_mail, msg.as_string())
        server.quit()
        return "Good job!"

    except Exception as _ex:
        print(f"{_ex}\nCheck your password or email address\n")

# отправка сообщений по почте
def send_message_to_one():

    name = listen()
    current_rate = 0
    real_name = ''
    other_mail = ''

    for key in data_set.posts.keys():
        rate = fuzz.ratio(key, name)
        if rate > current_rate:
            current_rate = rate
            real_name = key
            other_mail = data_set.posts[key]

    if (current_rate < 30):
        say("такого человека я не знаю")
        say("мне добавить его в список. да или нет")

        answer = listen()

        if answer == "да":
            post = input()
            data_set.posts[name] = post
        else:
            return


    mail = 'KARum2004@yandex.ru'
    say("что написать в письме")
    message = listen()

    with open("source.txt", 'r', encoding='utf-8') as file:
        password = file.readline()

    msg = MIMEText(f'{message}', 'plain', 'utf-8')
    msg['Subject'] = Header('От голосового помощника Кеши', 'utf-8')
    msg['From'] = mail
    msg['To'] = other_mail
    server = smtplib.SMTP('smtp.yandex.ru', 587, timeout=10)

    try:
        server.starttls()
        server.login(mail, password)
        server.sendmail(msg['From'], other_mail, msg.as_string())
        server.quit()
        return "Good job!"

    except Exception as _ex:
        print(f"{_ex}\nCheck your password or email address\n")

def search_wikipedia():

    user_query = listen()

    wiki_wiki = wikipediaapi.Wikipedia(
        language='ru',
        user_agent='SmartAssistant/1.0')
    page = wiki_wiki.page(user_query)
    if page.exists():
        text = page.summary
        desktop_file = os.path.join(os.path.join(os.environ['USERPROFILE']), 'Desktop' + "\\" + "wiki_result.txt")
        with open(desktop_file, "w", encoding='utf-8') as file:
            file.write(text)

        say(text)
    else:
        say("По вашему запросу ничего не найдено в Википедии.")

def offwork():
    sys.exit()

def cash_rate():

    currency = listen()
    total_rate = 0
    value = ''
    for name in data_set.money:
        current_rate = fuzz.ratio(name, currency)
        if current_rate > total_rate:
            total_rate = current_rate
            value = name

    if total_rate > 30:
        currency = value
    else:
        currency = ''

    if currency in data_set.money.keys():
        value = data_set.money[currency]
        rates = ExchangeRates(str(datetime.datetime.now())[:10])
        currency_data = list(filter(lambda el: el.code == value, rates.rates))[0]
        print(f"{currency} - {currency_data.rate} рублей")
        say(f"{currency} - {currency_data.rate}")
    else:
        say("я пока не знаю о такой валюте")

def weather_forecast():

    config_dict = get_default_config()
    config_dict['language'] = 'ru'
    owm = pyowm.OWM('1caaa63b8672e96b288306695fd081ed', config_dict)
    manager = owm.weather_manager()

    city = listen()

    try:
        weather = manager.weather_at_place(city).weather
        forecast = weather.detailed_status

        temperature = weather.temperature('celsius').get('temp')
        temperature = round(temperature)

        say(f'Температура в {city} сейчас {temperature}, {forecast}')
    except Exception:
        say("Похоже город неверный!")


def search_person_vk():
    name = listen().split()

    if not name:
        say("Имя для поиска не указано.")
        return

    formatted_name = " ".join(part.capitalize() for part in name)
    vk_search_term_encoded = urllib.parse.quote(formatted_name)
    vk_url = "https://vk.com/people/" + vk_search_term_encoded
    webbrowser.get().open(vk_url)
    say("Поиск в социальной сети ВКонтакте выполнен.")

def say(text):
    engine = pyttsx3.init()
    engine.setProperty('rate', 180)

    engine.say(text)
    engine.runAndWait()

def callback(indata, frames, time, status):
    q.put(bytes(indata))

def listen():
    print("Я вас слушаю >>>")
    with sd.RawInputStream(samplerate=samplerate, blocksize=16000, device=device[0],
                    dtype='int16', channels=1, callback=callback):

        rec = vosk.KaldiRecognizer(model, samplerate)
        while True:
            data = q.get()
            #когда будет пауза он выводит весь получившийся текст
            if rec.AcceptWaveform(data):
                data = json.loads(rec.Result())['text']
                return data

def recognise(model, tokenizer, lbl_encoder):
    while True:
        text = listen()
        print(text)

        trg = data_set.triggers.intersection(text.split())
        if not trg:
            continue

        text.replace(list(trg)[0], '')

        max_len = 20
        result = model.predict(keras.preprocessing.sequence.pad_sequences(tokenizer.texts_to_sequences([text]),
                                                                          truncating='post', maxlen=max_len))
        tag = lbl_encoder.inverse_transform([np.argmax(result)])

        with open("intents.json", encoding='utf-8') as file:
            data = json.load(file)

        for i in data['intents']:
            if i['tag'] == tag:
                parts = i['tag'].split(' ')
                state = parts[0]
                function = parts[1]
                if state == 'active':
                    say(random.choice(i['responses']))
                    exec(function + '()')
                else:
                    say(random.choice(i['responses']))