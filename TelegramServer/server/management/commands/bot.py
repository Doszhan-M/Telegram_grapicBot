from .bot_files.extensions import give_me_report, welcome_text, start_btn, empty_user, make_payment, choice_sum, \
    new_report, confirm_send_payment, yes_arrive, no_arrive, other_sum, logger
from .bot_files.settings import bot
from django.core.management.base import BaseCommand
from server.models import Payment, Score, Lender, Borrower
from telebot import types
from urllib.request import urlopen
import telebot
import os, time
from TelegramServer.settings import BASE_DIR
import logging


class Command(BaseCommand):
    help = '7-20-25'
    temp_int_data = 0  # сервис переменная

    def handle(self, *args, **options):
        logger()  # Инициализация логгера
        logging.info('Star telegram bot')

        # Добавить сумму займа
        def add_sum(message):
            try:
                text = f'Вы ввели сумму {int(message.text)}. Если это верно, то подтвердите:'
                self.temp_int_data = int(message.text)
                keyboard1 = types.InlineKeyboardMarkup()  # Готовим кнопки
                key_yes = types.InlineKeyboardButton(text='Подтвердить', callback_data='yes')
                key_no = types.InlineKeyboardButton(text='Ввести повторно', callback_data='no')
                keyboard1.add(key_yes, key_no)  # И добавляем кнопку на экран
                bot.send_message(message.from_user.id, text, reply_markup=keyboard1)
            except ValueError:
                bot.send_message(message.from_user.id, 'Вам необходимо ввести целое число:', )
                bot.register_next_step_handler(message, add_sum)

        #  Добавить сумму займа
        def score(message):
            text = f"Добрый день {message.from_user.first_name}!"
            bot.send_message(message.from_user.id, text)
            bot.send_message(message.from_user.id, welcome_text)
            bot.send_message(message.from_user.id, 'Для начало работы вам необходимо ввести сумму займа:')
            bot.register_next_step_handler(message, add_sum)

        # Принять другую сумму
        def confirm_other_sum(message):
            try:
                text2 = f'Вы ввели сумму {int(message.text)}:'
                self.temp_int_data = int(message.text)
                keyboard1 = types.InlineKeyboardMarkup()  # Готовим кнопки
                key_yes = types.InlineKeyboardButton(text='Подтвердить', callback_data='other_yes')
                key_no = types.InlineKeyboardButton(text='Ввести повторно', callback_data='other_no')
                keyboard1.add(key_yes, key_no)  # И добавляем кнопку на экран
                bot.send_message(message.from_user.id, text2, reply_markup=keyboard1)
            except ValueError:
                bot.send_message(message.from_user.id, 'Вам необходимо ввести целое число:')
                bot.register_next_step_handler(message, confirm_other_sum)

        # На время отладки, для старта с нуля
        @bot.message_handler(commands=['erase_all_data'])
        def empty(message: telebot.types.Message):
            """Стереть все записи с базы данных"""
            Lender.objects.all().delete()
            Borrower.objects.all().delete()
            Payment.objects.all().delete()
            Score.objects.all().delete()
            logging.info('База данных очищена')

        # Основной алгоритм бота
        @bot.message_handler(commands=['start'])
        def start(message: telebot.types.Message):
            lenders = Lender.objects.filter(lender_id=message.from_user.id)  # займодатель
            borrowers = Borrower.objects.filter(borrower_id=message.from_user.id)  # заемщик

            # Проверяем, есть ли запись счетов в базе данных
            if Score.objects.count() == 0:
                score(message)
            # Определяем пользователя
            elif not lenders:
                # Если это бороуер то выполняет работу
                if borrowers:
                    make_payment(message)
                    give_me_report(message)
                    logging.info(f'Активность заемщика')
                else:
                    if Borrower.objects.count() == 1:
                        bot.send_message(message.from_user.id, welcome_text)
                        empty_user(message)
                    else:
                        empty_user(message)

            # Определяем пользователя
            elif not borrowers:
                # Если это лендер то выполняет работу
                if lenders:
                    give_me_report(message)
                    logging.info(f'Активность займодателя')
                else:
                    if Lender.objects.count() == 1:
                        bot.send_message(message.from_user.id, welcome_text)
                        empty_user(message)
                    else:
                        empty_user(message)

            # Обработчики нажатия на кнопки
            @bot.callback_query_handler(func=lambda call: True)
            def callback_worker(call):
                # Callback для формирования и передачи отчета
                if call.data == 'give_me_report':
                    os.chdir(BASE_DIR)
                    os.startfile("bot_runserver.vbs")  # vbs скрип запустить сервер джанго, для формирования отчета
                    time.sleep(3)
                    try:
                        page = urlopen('http://127.0.0.1:8000/')
                    except Exception: # Грубо, но так надо
                        time.sleep(2)
                        page = urlopen('http://127.0.0.1:8000/')
                        logging.info(f'Времени для старта сервера не хватило')
                    with open("Отчет.html", "wb") as report:
                        report.write(page.read())
                        logging.info(f'Отчет успешно отправлен {call.from_user.id}')
                    bot.send_document(call.from_user.id, open(r'Отчет.html', 'rb'))
                    return

                # Callback для перевода средств
                elif call.data == 'send_money':
                    choice_sum(call)
                elif call.data == '50':
                    new_report(50000)
                    confirm_send_payment(call, 50000)
                elif call.data == '100':
                    new_report(100000)
                    confirm_send_payment(call, 100000)
                elif call.data == 'other':
                    bot.send_message(call.from_user.id, 'Введите сумму перевода:')
                    bot.register_next_step_handler(message, confirm_other_sum)
                elif call.data == 'other_yes':
                    new_report(self.temp_int_data)
                    confirm_send_payment(call, self.temp_int_data)
                elif call.data == 'other_no':
                    other_sum(call)
                    bot.register_next_step_handler(message, confirm_other_sum)
                elif call.data == 'yes_arrive':
                    yes_arrive(call)
                    bot.answer_callback_query(callback_query_id=call.id, text='Подтверждено!', show_alert=True)
                    logging.info(f'Подтверждено займодетелем')
                elif call.data == 'no_arrive':
                    no_arrive(call)
                elif call.data == 'go_back':
                    bot.send_message(call.from_user.id, 'Отклонено')
                    logging.info(f'Отклонено займодетелем')
                elif call.data == 'check':
                    bot.send_message(call.from_user.id, 'Вы можете в любой момент подтвердить кнопкой выше')

                # Callback для определения статуса пользователей
                elif call.data == 'lender':
                    if Lender.objects.count() == 0:
                        Lender.objects.create(lender_id=call.from_user.id)
                        bot.send_message(call.from_user.id, 'Спасибо, вы зарегистрированы в качестве Займодателя')
                        start(call)
                        logging.info('Займодатель зарегистрирован')
                    else:
                        bot.send_message(call.from_user.id, 'Займодатель ранее был зарегистрирован')
                        start(call)
                elif call.data == 'borrower':
                    if Borrower.objects.count() == 0:
                        Borrower.objects.create(borrower_id=call.from_user.id)
                        bot.send_message(call.from_user.id, 'Спасибо, вы зарегистрированы в качестве Заемщика')
                        start(call)
                        logging.info('Заемщик зарегистрирован')
                    else:
                        bot.send_message(call.from_user.id, 'Заемщик ранее был зарегистрирован')
                        start(call)

                # Callback для начальной суммы
                elif call.data == 'yes':
                    Score.objects.create(total=self.temp_int_data, leftover=self.temp_int_data,
                                         payment_status='подтвержден', monthly_payment=0, total_payment=0, )
                    bot.send_message(call.from_user.id, 'Спасибо, данные успешно внесены в график погашения!')
                    start_btn(call)
                    logging.info(f'Начальная сумма определена')
                elif call.data == 'no':
                    start_btn(call)

        try:
            bot.polling(none_stop=True)
        except Exception:  # если бот упал по крайне неопределенным обстоятельствам, перезапускаем
            os.chdir(BASE_DIR)
            os.startfile("start_bot.vbs")
            logging.exception("Exception occurred")
