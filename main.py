#!/usr/bin/env python3.4
import sys
import time
import config
import datetime
import vk_api
import telebot
import threading
#import requests
#from requests.auth import HTTPBasicAuth

config.initConfig()

module = sys.modules[__name__]


#     _____                              _     _ _   
#    / ____|                            | |   (_) |  
#   | (___   ___  _ __ ___   ___     ___| |__  _| |_ 
#    \___ \ / _ \| '_ ` _ \ / _ \   / __| '_ \| | __|
#    ____) | (_) | | | | | |  __/   \__ \ | | | | |_ 
#   |_____/ \___/|_| |_| |_|\___|   |___/_| |_|_|\__|
#                                                    
#   Технические функции

#Получаем текущее время
def current_time():
	delta = datetime.timedelta( hours=3 )
	utc = datetime.timezone.utc
	fmt = '%H:%M:%S'
	time = ( datetime.datetime.now(utc) + delta )
	timestr = time.strftime(fmt)
	return timestr

# Проверка на наличие аттачментов в сообщении
def MsgHasAttachment( msg ):
	if not( msg.get( 'attachments' ) ):
		return False
	return True

# Получаем аттачменты из сообщения ВК
def getAttachments( msg ):

	AttachList = []

	for att in msg['attachments'][0:]:

		AttType = att.get('type')

		Attachment = att[AttType]

		if AttType == 'photo': # Проверка на тип фотографии

			# Различные типы фото
			if Attachment.get( 'photo_2560' ):
				attachments = Attachment.get( 'photo_2560' )
			elif Attachment.get( 'photo_1280' ):
				attachments = Attachment.get( 'photo_1280' )
			elif Attachment.get( 'photo_604' ):
				attachments = Attachment.get( 'photo_604' )
			elif Attachment.get( 'photo_130' ):
				attachments = Attachment.get( 'photo_130' )
			elif Attachment.get( 'photo_75' ):
				attachments = Attachment.get( 'photo_75' )

		elif AttType == 'doc': # Проверка на тип документа:
		# Про типы документов можно узнать тут: https://vk.com/dev/objects/doc
			DocType = Attachment.get('type')
			if DocType != 3 and DocType != 4 and DocType != 5:
				AttType = 'file'
			if Attachment.get( 'url' ):
				attachments = Attachment.get( 'url' )

		elif AttType == 'sticker': # Проверка на стикеры:
			# Можно 256 или 512, но будет слишком огромная пикча
			if Attachment.get( 'photo_128' ):
				attachments = Attachment.get( 'photo_128' )

		elif AttType == 'audio':
			if Attachment.get( 'url' ):
				attachments = Attachment.get( 'url' )

		elif AttType == 'video':

			OwnerId = str( Attachment.get( 'owner_id' ) )
			VideoId = str( Attachment.get( 'id' ) )
			Accesskey = str( Attachment.get( 'access_key' ) )

			FullURL = str( OwnerId + '_' + VideoId + '_' + Accesskey)

			attachments = module.vk.video.get(videos = FullURL )['items'][0].get('player')

		# Неизвестный тип?
		else:

			attachments = None

		AttachList.append( { 	'type':AttType,
								'link':attachments } )

	#print( AttachList )

	return AttachList

# Проверка на наличие перешлённых сообщений
# P.S. Нужно добавить сложение текста в сообщении перед перешлённым сообщением и ID того, кто переслал текст....
# Когда-нибудь обязательно переделаю архитектуру, но пока что пусть будет так
def CheckFwdMessages( msg ):
	if not( msg.get( 'fwd_messages' ) ):
		return False

	# Рекурсивное извлечение данных из перешлённого сообщения
	FwdMsg = BaseChecks( msg.get( 'fwd_messages' )[0] )

	return '\n\n | ' + FwdMsg[0], FwdMsg[1]

# Основная проверка на наличие различных плюшек в сообщении
def BaseChecks( msg ):

	mbody = msg.get( 'body' )

	# Проверка на наличие пересланных сообщений
	FwdMessages = CheckFwdMessages( msg )

	if FwdMessages:
		return FwdMessages[0], FwdMessages[1]

	if( MsgHasAttachment( msg ) ):
		attachments = getAttachments( msg )
	else:
		attachments = None

	return mbody, attachments

#    _____          _ _               _       
#   |  __ \        | (_)             | |      
#   | |__) |___  __| |_ _ __ ___  ___| |_ ___ 
#   |  _  // _ \/ _` | | '__/ _ \/ __| __/ __|
#   | | \ \  __/ (_| | | | |  __/ (__| |_\__ \
#   |_|  \_\___|\__,_|_|_|  \___|\___|\__|___/
#                                             
#  Функции, принимающие и отправляющие сообщения ВК <==> Telegram

def CheckRedirect_vk( msg ):

	userid = str( msg.get( 'user_id' ) )
	chatid = str( msg.get( 'chat_id' ) )

	#print( str( config.getCell( 'vk_' + chatid) ) )

	# Сделано на костылях, это я знаю
	# Возможно, когда-нибудь я займусь оптимизацией кода....
	# ( Когда-нибудь... )

	if not config.getCell( 'vk_' + chatid) is None:

		time = current_time()
		dataname = module.vk.users.get( user_ids = userid )
		firstname = dataname[0]['first_name']
		lastname = dataname[0]['last_name']

		# Проверка на аттачменты, пересланные сообщения, видео...
		OtherThings = BaseChecks( msg )

		TransferMessageToTelegram( time, chatid, firstname, lastname, OtherThings[0], OtherThings[1] )

		return False

	elif not config.getCell( 'vk_' + userid) is None:

		time = current_time()
		dataname = module.vk.users.get( user_ids = userid )
		firstname = dataname[0]['first_name']
		lastname = dataname[0]['last_name']
		mbody = msg.get( 'body' )

		if( MsgHasAttachment( msg ) ):
			attachments = getAttachments( msg )
		else:
			attachments = None

		TransferMessageToTelegram( time, userid, firstname, lastname, mbody, attachments )

		return False

	return True

def TransferMessageToVK( chatid, text, Attachment ):
	if Attachment is None:
		try:
			module.vk.messages.send( chat_id = config.getCell( 't_' + chatid ), message = text )
		except vk_api.ApiError as error_msg:
			module.vk.messages.send( user_id = config.getCell( 't_' + chatid ), message = text )
		#print( 'Сообщение успешно отправлено! ( ' + text + ' )' )
	else:
		None

		# Я пытался... потом доделаю)

		#print( Attachment )
		#Lel = 'https://api.telegram.org/file/bot{0}/{1}'.format( config.getCell( 'telegram_token' ), Attachment )
		#Req = requests.get('https://ezgif.com/webp-to-png?url=https://api.telegram.org/file/bot{0}/{1}'.format( config.getCell( 'telegram_token' ), Attachment ) )
		#endpoint = "https://sandbox.zamzar.com/v1/jobs"
		#source_file = "https://api.telegram.org/file/bot{0}/{1}".format( config.getCell( 'telegram_token' ), Attachment )
		#target_format = "jpg"
		# http://www.zamzar.com/convert/webp-to-jpg/
		# https://developers.zamzar.com/docs#section-Starting_a_new_job_for_a_URL
		# https://api.zamzar.com/v1/

		#data_content = {'source_file': source_file, 'target_format': target_format}
		#res = requests.post(endpoint, data=data_content, auth=HTTPBasicAuth(config.getCell( 'api_key' ), ''))

		#print( res.json() )

	return False

def CheckRedirect_telegram( chatid, text, Attachment ):
	if not config.getCell( 't_' + chatid ) is None:
		TransferMessageToVK( chatid, text, Attachment )
		return False

def TransferMessageToTelegram( time, idd, firstname, lastname, mbody, attachments ):

	NiceText = str( time + ' | ' + firstname + ' ' + lastname + ': ' + mbody )

	if not attachments is None:

		module.bot.send_message( config.getCell( 'vk_' + idd ), NiceText )

		for j in attachments[0:]:

			AttType = j.get('type')
			Link = j.get('link')

			if AttType == 'photo' or AttType == 'sticker':
				module.bot.send_photo( config.getCell( 'vk_' + idd ), Link )

			elif AttType == 'doc' or AttType == 'gif' or AttType == 'audio':
				module.bot.send_document( config.getCell( 'vk_' + idd ), Link )

			elif AttType == 'file':
				module.bot.send_message( config.getCell( 'vk_' + idd ), Link )

			elif AttType == 'video':

				# Потому что в ВК нельзя нормальной ссылкой отправить видео как видео -_-
				module.bot.send_message( config.getCell( 'vk_' + idd ), Link )

			else:
				print( 'Неизвестный тип аттачмента' )

	else:
		module.bot.send_message( config.getCell( 'vk_' + idd ), NiceText )

#   __      ___    
#   \ \    / / |   
#    \ \  / /| | __
#     \ \/ / | |/ /
#      \  /  |   < 
#       \/   |_|\_\
#                  
#

def captcha_handler(captcha):
	key = input( "Enter Captcha {0}: ".format( captcha.get_url() ) ).strip()
	return captcha.try_again(key)

def init_vk():

	login = config.getCell( 'vk_login' )
	password = config.getCell( 'vk_password' )

	print( "login in vk as: " + login )

	vk_session = vk_api.VkApi( login, password, captcha_handler=captcha_handler )

	try:
		vk_session.auth()
	except vk_api.AuthError as error_msg:
		print( error_msg )

	module.vk = vk_session.get_api() # Важная штука

	input_vk()

def input_vk():
	
	while True:

		try:
			#Ставим онлайн боту, чому бы и нет?
			module.vk.account.setOnline()

			rawMessages = module.vk.messages.get(out = 0, count = config.getCell('vk_msgForPick') )

			for msg in rawMessages['items']:
				if msg['read_state'] == 0:
					if not msg.get( 'chat_id' ) is None:
						module.vk.messages.markAsRead(messages_ids = msg['id'], peer_id = 2000000000 + msg['chat_id'])
					else:
						module.vk.messages.markAsRead(messages_ids = msg['id'], peer_id = msg['user_id'])

					CheckRedirect_vk( msg )

		# Чтобы не вылетало, а работало дальше
		except BaseException:
		#	print( 'Что-то пошло не так...' )
			continue


#    _______   _                                
#   |__   __| | |                               
#      | | ___| | ___  __ _ _ __ __ _ _ __ ___  
#      | |/ _ \ |/ _ \/ _` | '__/ _` | '_ ` _ \ 
#      | |  __/ |  __/ (_| | | | (_| | | | | | |
#      |_|\___|_|\___|\__, |_|  \__,_|_| |_| |_|
#                      __/ |                    
#                     |___/                     


def listener( messages ):
	for m in messages:

		if m.content_type == 'text':

			# На команду 'Дай ID' кидает ID чата
			if m.text == 'Дай ID':
				module.bot.send_message( m.chat.id, str( m.chat.id ) )
				continue

			CheckRedirect_telegram( str( m.chat.id ), str( m.text ), None )

		# Ещё недопилено
		elif m.content_type == 'sticker':

			FilePath = module.bot.get_file( m.sticker.file_id ).file_path

			CheckRedirect_telegram( str( m.chat.id ), str( m.text ), str( FilePath ) )

		#	print( 'https://api.telegram.org/file/bot{0}/{1}'.format( config.getCell( 'telegram_token' ), FilePath ) )


def init_telegram():

	module.bot = telebot.TeleBot( config.getCell( 'telegram_token' ) )
	print( "Successfully loginned in telegram!")
	input_telegram()

def input_telegram():
	module.bot.set_update_listener( listener )
	module.bot.polling( none_stop=False )


#    ______               _       
#   |  ____|             | |      
#   | |____   _____ _ __ | |_ ___ 
#   |  __\ \ / / _ \ '_ \| __/ __|
#   | |___\ V /  __/ | | | |_\__ \
#   |______\_/ \___|_| |_|\__|___/
#
# Проверка на различные события

#Проверка на заявки в друзья
def checknewfriends():
	newfriends = module.vk.friends.getRequests( out=0, count=1, need_viewed=1 ) # Смотрим, если ли заявки в друзья
	if newfriends['count'] != 0:
		module.vk.friends.add( user_id= newfriends['items'] ) # Добавляем человека в друзья

def init_events():
	while True:
		time.sleep(5)
		# Воткнул сюда проверку на наличие подписчиков, чтобы не спаммить функцией в цикле...
		if config.getCell( 'vk_AddFriends' ) == 1:
			checknewfriends()


#    ______ _             _      
#   |  ____(_)           | |     
#   | |__   _ _ __   __ _| | ___ 
#   |  __| | | '_ \ / _` | |/ _ \
#   | |    | | | | | (_| | |  __/
#   |_|    |_|_| |_|\__,_|_|\___|
#                                
# Пихаем функции в потоки

t1 = threading.Thread( target=init_vk )
t2 = threading.Thread( target=init_telegram )
t3 = threading.Thread( target=init_events )

t1.start()
t2.start()
t3.start()
t1.join()
t2.join()
t3.join()