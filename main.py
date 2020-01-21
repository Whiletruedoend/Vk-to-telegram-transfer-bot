#!/usr/lib/python3 python
# -*- coding: utf-8 -*-
import os
import sys
import config
import db
import random
import datetime
import vk_api
import telebot
import threading
import urllib.request as ur
from PIL import Image # Для преобразования изображений из webp в PNG

config.initConfig()

module = sys.modules[__name__]

# Код настоятельно рекомендуется читать снизу вверх!

#    _______        _     
#   |__   __|      | |    
#      | | ___  ___| |__  
#      | |/ _ \/ __| '_ \ 
#      | |  __/ (__| | | |
#      |_|\___|\___|_| |_|
#                         
#   Технические функции

# Получаем текущее время
def current_time():
	delta = datetime.timedelta( hours=3 )
	utc = datetime.timezone.utc
	fmt = '%H:%M:%S'
	time = ( datetime.datetime.now(utc) + delta )
	timestr = time.strftime(fmt)
	return timestr

# Получение имени пользователя
def getUserName( msg ):
	# Для приёма личных сообщений когда пишут через группу
	if ( int( msg.get('from_id') ) < 0 ):
		return None
	else:
		dataname = module.vk.users.get( user_ids = msg.get('from_id') )
		name = str ( dataname[0]['first_name'] + ' ' + dataname[0]['last_name'] )
	return name

def getUserTName( msg ):
	if msg.last_name is None:
		userName = str( msg.first_name )
	else:
		userName = str( msg.first_name + " " + msg.last_name )
	return userName

# Проверка на наличие аттачментов в сообщении
def checkAttachments( msg, idd ):
	if not( msg.get( 'attachments' ) ):
		return False
	transferAttachmentsToTelegram( idd, getAttachments( msg ) )
	return True

# Получаем аттачменты из сообщения ВК
def getAttachments( msg ):

	attachList = []

	for att in msg['attachments'][0:]:

		attType = att.get( 'type' )

		attachment = att[attType]

		if attType == 'photo': # Проверка на тип фотографии

			for photoType in attachment.get('sizes')[0:]:
				if photoType.get('type') == 'x': # <=604x604
					attachments = photoType.get('url')
				if photoType.get('type') == 'y': # >605x605
					attachments = photoType.get('url')
				if photoType.get('type') == 'z': # <=1280x720
					attachments = photoType.get('url')
				if photoType.get('type') == 'w':# >1280x720
					attachments = photoType.get('url') # <=2560x1440
					attType = 'other'

		elif attType == 'doc': # Проверка на тип документа:
		# Про типы документов можно узнать тут: https://vk.com/dev/objects/doc
			docType = attachment.get( 'type' )
			if docType != 3 and docType != 4 and docType != 5:
				attType = 'other'
			if attachment.get( 'url' ):
				attachments = attachment.get( 'url' )

		elif attType == 'sticker': # Проверка на стикеры:
			for sticker in attachment.get( 'images' )[0:]:
				# Можно 256 или 512, но будет слишком огромная пикча
				if sticker.get('width') == 128:
					attachments = sticker.get( 'url' )

		elif attType == 'audio':
			attachments = str ( '𝅘𝅥𝅮 ' + attachment.get('artist') + ' - ' + 
				attachment.get('title') + ' 𝅘𝅥𝅮' )
			attType = 'other'

		elif attType == 'audio_message':
			attachments = attachment.get('link_ogg')

		elif attType == 'video':

			ownerId = str( attachment.get( 'owner_id' ) )
			videoId = str( attachment.get( 'id' ) )
			accesskey = str( attachment.get( 'access_key' ) )

			fullURL = str( ownerId + '_' + videoId + '_' + accesskey)

			attachments = module.vk.video.get(videos = fullURL )['items'][0].get('player')

		# Неизвестный тип?
		else:

			attachments = None

		attachList.append( { 	'type':attType,
								'link':attachments } )

	#print( attachList )

	return attachList

# Проверка чата ВК на различные события
def checkEvents( msg, chatid ):

	if not ( msg['last_message'].get( 'action' ) ):
		return None # И так сойдёт

	event = msg['last_message']['action'].get( 'type' )
	userName = getUserName( msg['last_message'] )

	# Ниже проверям наш чат на различные события
	# См. https://vk.com/dev/objects/message

	if event == 'chat_title_update':
		eObject = str( msg['last_message']['action'].get( 'text' ) )
		mbody = " *** " + userName + " изменил(а) название беседы на " + eObject + " ***"

	elif event == 'chat_invite_user':
		dataname = module.vk.users.get( user_ids = msg['last_message']['action'].get( 'member_id' ) )
		eObject = str ( dataname[0]['first_name'] + ' ' + dataname[0]['last_name'] )
		mbody = " *** " + userName + " пригласил(а) в беседу " + eObject + " ***"

	elif event == 'chat_kick_user':
		dataname = module.vk.users.get( user_ids = msg['last_message']['action'].get( 'member_id' ) )
		eObject = str ( dataname[0]['first_name'] + ' ' + dataname[0]['last_name'] )
		mbody = " *** " + userName + " кикнул(а) из беседы " + eObject + " ***"

	elif event == 'chat_photo_update':
		mbody = " *** " + userName + " обновил(а) фото беседы: ***"

	elif event == 'chat_photo_remove':
		mbody = " *** " + userName + " удалил(а) фото беседы! ***"

	elif event == 'chat_pin_message':
		eObject = str( msg['last_message']['action'].get( 'message' ) )
		if( eObject ):
			mbody = " *** " + userName + " закрепил(а): " + eObject + " ***"
		else:
			mbody = " *** " + userName + " закрепил(а) сообщение! ***"

	elif event == 'chat_unpin_message':
		mbody = " *** " + userName + " открепил(а) сообщение! ***"

	elif event == 'chat_create':
		print( 'Беседа была создана!' )

	else:
		return None

	transferMessagesToTelegram( chatid, None, mbody, None )

# Проверка на наличие перешлённых сообщений
def getFwdMessages( msg, idd ):

	if not( msg.get( 'fwd_messages' ) ):
		return None # И так сойдёт

	fwdList = []
	fwdMsg = msg.get( 'fwd_messages' )

	while not fwdMsg is None:

		userName = getUserName( fwdMsg[0] )

		fwdList.append( { 'body':fwdMsg[0].get( 'text' ), 'userName':userName } )

		checkAttachments( fwdMsg[0], idd )

		fwdMsg = fwdMsg[0].get( 'fwd_messages' )

	#print( fwdList )

	return fwdList

#    _____          _ _               _       
#   |  __ \        | (_)             | |      
#   | |__) |___  __| |_ _ __ ___  ___| |_ ___ 
#   |  _  // _ \/ _` | | '__/ _ \/ __| __/ __|
#   | | \ \  __/ (_| | | | |  __/ (__| |_\__ \
#   |_|  \_\___|\__,_|_|_|  \___|\___|\__|___/
#                                             
#  Функции, принимающие и отправляющие сообщения ВК <==> Telegram

def checkRedirect_vk( msg ):

	chatid = str( msg['conversation']['peer']['local_id'] )

	# Проверка на существование переадресации в конфиге
	if not config.getCell( "vk_" + chatid ) is None:

		forwardMessage = getFwdMessages( msg['last_message'], chatid )

		userName = getUserName( msg['last_message'] )
		mbody = msg['last_message'].get( 'text' )

		# Чтобы при событии не посылалось пустое сообщение
		if checkEvents( msg, chatid ) is None:
			transferMessagesToTelegram( chatid, userName, mbody, forwardMessage )

		# Проверка на аттачменты, пересланные сообщения, видео...
		# Проверка сделана, чтобы исключить повтор картинки
		if forwardMessage is None:
			checkAttachments( msg['last_message'], chatid )

		return False

def transferMessageToVK( chatid, text, fromUser, attachment ):

	if ( config.getCell('telegram_SendName') ):
		time = current_time()
		text = str( time + ' | ' + fromUser + ': ' + text )

	randid = random.randint(-9223372036854775808, +9223372036854775807) #int64

	if attachment is None:

		try:
			module.vk.messages.send( chat_id = config.getCell( 't_' + chatid ), message = text, random_id=randid )
		except vk_api.ApiError as error_msg:
			module.vk.messages.send( user_id = config.getCell( 't_' + chatid ), message = text, random_id=randid )
		#print( 'Сообщение успешно отправлено! ( ' + text + ' )' )

	else:

		getSticker = db.checkSticker( attachment )

		# Если стикер не найден в БД
		if getSticker is None:
			stickerURL = 'https://api.telegram.org/file/bot{0}/{1}'.format( config.getCell( 'telegram_token' ), attachment )
			saveSticker( stickerURL, attachment )
			getSticker = db.checkSticker( attachment )

		#print( getSticker )

		try:
			module.vk.messages.send( chat_id = config.getCell( 't_' + chatid ), message = "", attachment = getSticker, random_id=randid )
		except vk_api.ApiError as error_msg:
			module.vk.messages.send( user_id = config.getCell( 't_' + chatid ), message = "", attachment = getSticker, random_id=randid )

	return False

def checkRedirect_telegram( chatid, text, fromUser, attachment ):
	if not config.getCell( 't_' + chatid ) is None:
		transferMessageToVK( chatid, text, fromUser, attachment )
		return False

# Посылаем простые сообщения в Telegram
# Идея: сделать в будущем наклонные столбики, теперь главное не забыть
def transferMessagesToTelegram( idd, userName, mbody, fwdList ):

	# Условие выполняется в случае какого-либо события
	if userName is None:
		if mbody:
			module.bot.send_message( config.getCell( 'vk_' + idd ), str( mbody ) )
		return False

	time = current_time()
	niceText = str( time + ' | ' + userName + ': ' + mbody )

	if not fwdList is None:

		forwardText = ''

		for f in fwdList[0:]:
			forwardText = forwardText + str( ' | ' + f.get( 'userName' ) + ':' + ' ' + f.get( 'body' ) + ' \n\n' )

		module.bot.send_message( config.getCell( 'vk_' + idd ), niceText + '\n\n' + forwardText )

	else:
		module.bot.send_message( config.getCell( 'vk_' + idd ), niceText )

# Посылаем аттачменты в Telegram
def transferAttachmentsToTelegram ( idd, attachments ):

	for j in attachments[0:]:

		attType = j.get( 'type' )
		link = j.get( 'link' )

		if attType == 'photo' or attType == 'sticker':
			module.bot.send_photo( config.getCell( 'vk_' + idd ), link )

		elif attType == 'doc' or attType == 'gif' or attType == 'audio_message':
			module.bot.send_document( config.getCell( 'vk_' + idd ), link )

		elif attType == 'other':
			module.bot.send_message( config.getCell( 'vk_' + idd ), link )

		elif attType == 'video':

			# Потому что в ВК не может отправить полную ссылку на файл видео -_-
			module.bot.send_message( config.getCell( 'vk_' + idd ), link )

		else:
			module.bot.send_message( config.getCell( 'vk_' + idd ), '( Неизвестный тип аттачмента )' )

#   __      ___    
#   \ \    / / |   
#    \ \  / /| | __
#     \ \/ / | |/ /
#      \  /  |   < 
#       \/   |_|\_\
#                  
#

# При двухфакторной аутентификации вызывается эта функция
def auth_handler():

	key = input("Enter authentication code: ")
	# True - сохранить, False - не сохранять
	remember_device = True

	return key, remember_device

# Каптча
def captcha_handler( captcha ):
	key = input( "Enter Captcha {0}: ".format( captcha.get_url() ) ).strip()
	return captcha.try_again(key)

def init_vk():

	login = config.getCell( 'vk_login' )
	password = config.getCell( 'vk_password' )
	app = config.getCell( 'app_id' )

	print( "login in vk as: " + login )

	global vk_session

	vk_session = vk_api.VkApi( login, password, app_id=app, auth_handler=auth_handler, captcha_handler=captcha_handler )

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

			# Проверка на наличие подписчиков
			if ( config.getCell('vk_AddFriends') ):
				checknewfriends()

			rawMessages = module.vk.messages.getConversations( filter='unread', count=config.getCell('vk_msgForPick') )['items'][0]
			msg = rawMessages['conversation']['peer']
			module.vk.messages.markAsRead( messages_ids = msg['local_id'], peer_id = msg['id'] )

			checkRedirect_vk( rawMessages )

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

			checkRedirect_telegram( str( m.chat.id ), str( m.text ), getUserTName(m.from_user), None )

		elif m.content_type == 'sticker':

			if not ( config.getCell('vk_EnableStickers') ):
				return False

			filePath = module.bot.get_file( m.sticker.file_id ).file_path

			checkRedirect_telegram( str( m.chat.id ), str( m.text ), getUserTName(m.from_user), str( filePath ) )


def init_telegram():

	module.bot = telebot.TeleBot( config.getCell( 'telegram_token' ) )
	print( "Successfully loginned in telegram!")
	input_telegram()

def input_telegram():

	if ( config.getCell('telegram_useProxy') ):
		proxyType = str( config.getCell('p_type') )
		proxyUserInfo = str( config.getCell('p_user') + ':' + config.getCell('p_password') )
		proxyData = str( config.getCell('p_host') + ':' + config.getCell('p_port') )
		telebot.apihelper.proxy = { 
		'http': '%s://%s@%s' % ( proxyType, proxyUserInfo, proxyData ),
		'https': '%s://%s@%s' % ( proxyType, proxyUserInfo, proxyData )
		}

	module.bot.set_update_listener( listener )
	while True: # Костыль на случай timeout'a
		try:
			module.bot.polling(none_stop=False)
		except:
			continue

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

#     _____ _   _      _                 
#    / ____| | (_)    | |                
#   | (___ | |_ _  ___| | _____ _ __ ___ 
#    \___ \| __| |/ __| |/ / _ \ '__/ __|
#    ____) | |_| | (__|   <  __/ |  \__ \
#   |_____/ \__|_|\___|_|\_\___|_|  |___/
#                                        
#                                        

# Загрузка стикеров в ВК
def addStickerIntoVK( path, sticker ):

	stickerList = []
	ourFile = path + sticker

	upload = vk_api.VkUpload( vk_session )
	photo = upload.photo( ourFile + ".png", album_id = config.getCell( 'vk_album_id' ) )

	if ( config.getCell('vk_detelestickers') ):
		os.remove( ourFile + ".png" )

	ourVK = 'photo{}_{}'.format( photo[0]['owner_id'], photo[0]['id'] )

	stickerList.append( { 'sticker_t':ourFile,
						  'sticker_vk':ourVK } )

	return stickerList

def saveSticker( stickerURL, attachment ):

	attachment = attachment.split('/')

	content = ur.urlopen( stickerURL ).read()

	path = attachment[0] + '/'
	if not os.path.exists( path ):
		os.makedirs( path )

	# Перекодирование из webp в png

	imageWebp = path + attachment[1]

	out = open( imageWebp, 'wb' )
	out.write( content )
	out.close()

	img = Image.open(imageWebp)

	if ( config.getCell('vk_sticker_EnableScale') ):
		scale = config.getCell( 'vk_sticker_size' )
		img.thumbnail((scale, scale))
	img.save( imageWebp + ".png", "PNG")
	os.remove( imageWebp )

	#print( 'Sticker saved!' )

	stickers = addStickerIntoVK( path, attachment[1] )
	db.addStickerIntoDb( stickers )

# Разработчикам на заметку:
# Telegram та ещё поехавшая вещь, иногда аттачменты идут с расширением файла, иногда - без него
# Из-за этого я долго не мог понять, почему одни стикеры отправляются нормально, а другие - выдают ошибку при отправке

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

t1.start()
t2.start()
t1.join()
t2.join()