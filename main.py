#!/usr/bin/env python3.4
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
def GetUserName( msg ):
	dataname = module.vk.users.get( user_ids = msg.get('from_id') )
	UserName = str ( dataname[0]['first_name'] + ' ' + dataname[0]['last_name'] )
	return UserName

def GetUserTName( msg ):
	if msg.last_name is None:
		UserName = str( msg.first_name )
	else:
		UserName = str( msg.first_name + " " + msg.last_name )
	return UserName

# Проверка на наличие аттачментов в сообщении
def CheckAttachments( msg, idd ):
	if not( msg.get( 'attachments' ) ):
		return False
	TransferAttachmentsToTelegram( idd, getAttachments( msg ) )
	return True

# Получаем аттачменты из сообщения ВК
def getAttachments( msg ):

	AttachList = []

	for att in msg['attachments'][0:]:

		AttType = att.get( 'type' )

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
			DocType = Attachment.get( 'type' )
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

# Проверка чата ВК на различные события
def CheckEvents( msg, chatid ):

	if not ( msg['last_message'].get( 'action' ) ):
		return None # И так сойдёт

	Event = msg['last_message']['action'].get( 'type' )
	UserName = GetUserName( msg['last_message'] )

	# Ниже проверям наш чат на различные события
	# См. https://vk.com/dev/objects/message

	if Event == 'chat_title_update':
		Object = str( msg['last_message']['action'].get( 'text' ) )
		mbody = " *** " + UserName + " изменил(а) название беседы на " + Object + " ***"

	elif Event == 'chat_invite_user':
		dataname = module.vk.users.get( user_ids = msg['last_message']['action'].get( 'member_id' ) )
		Object = str ( dataname[0]['first_name'] + ' ' + dataname[0]['last_name'] )
		mbody = " *** " + UserName + " пригласил(а) в беседу " + Object + " ***"

	elif Event == 'chat_kick_user':
		dataname = module.vk.users.get( user_ids = msg['last_message']['action'].get( 'member_id' ) )
		Object = str ( dataname[0]['first_name'] + ' ' + dataname[0]['last_name'] )
		mbody = " *** " + UserName + " кикнул(а) из беседы " + Object + " ***"

	elif Event == 'chat_photo_update':
		Object = str( msg['last_message'].get( 'photo_200' ) )
		mbody = " *** " + UserName + " обновил(а) фото беседы: ***"

	elif Event == 'chat_photo_remove':
		mbody = " *** " + UserName + " удалил(а) фото беседы! ***"

	elif Event == 'chat_create':
		print( 'Беседа была создана!' )

	else:
		return None

	TransferMessagesToTelegram( chatid, None, mbody, None )

# Проверка на наличие перешлённых сообщений
def GetFwdMessages( msg, idd ):

	if not( msg.get( 'fwd_messages' ) ):
		return None # И так сойдёт

	FwdList = []
	FwdMsg = msg.get( 'fwd_messages' )

	while not FwdMsg is None:

		UserName = GetUserName( FwdMsg[0] )

		FwdList.append( { 'body':FwdMsg[0].get( 'text' ), 'UserName':UserName } )

		CheckAttachments( FwdMsg[0], idd )

		FwdMsg = FwdMsg[0].get( 'fwd_messages' )

	#print( FwdList )

	return FwdList

#    _____          _ _               _       
#   |  __ \        | (_)             | |      
#   | |__) |___  __| |_ _ __ ___  ___| |_ ___ 
#   |  _  // _ \/ _` | | '__/ _ \/ __| __/ __|
#   | | \ \  __/ (_| | | | |  __/ (__| |_\__ \
#   |_|  \_\___|\__,_|_|_|  \___|\___|\__|___/
#                                             
#  Функции, принимающие и отправляющие сообщения ВК <==> Telegram

def CheckRedirect_vk( msg ):

	chatid = str( msg['conversation']['peer']['local_id'] )

	# Проверка на существование переадресации в конфиге
	if not config.getCell( "vk_" + chatid ) is None:

		ForwardMessage = GetFwdMessages( msg['last_message'], chatid )

		UserName = GetUserName( msg['last_message'] )
		mbody = msg['last_message'].get( 'text' )

		# Чтобы при событии не посылалось пустое сообщение
		if CheckEvents( msg, chatid ) is None:
			TransferMessagesToTelegram( chatid, UserName, mbody, ForwardMessage )

		# Проверка на аттачменты, пересланные сообщения, видео...
		# Проверка сделана, чтобы исключить повтор картинки
		if ForwardMessage is None:
			CheckAttachments( msg['last_message'], chatid )

		return False

def TransferMessageToVK( chatid, text, fromUser, Attachment ):

	if ( config.getCell('telegram_SendName') ):
		time = current_time()
		text = str( time + ' | ' + fromUser + ': ' + text )

	randid = random.randint(-9223372036854775808, +9223372036854775807) #int64

	if Attachment is None:

		try:
			module.vk.messages.send( chat_id = config.getCell( 't_' + chatid ), message = text, random_id=randid )
		except vk_api.ApiError as error_msg:
			module.vk.messages.send( user_id = config.getCell( 't_' + chatid ), message = text, random_id=randid )
		#print( 'Сообщение успешно отправлено! ( ' + text + ' )' )

	else:

		GetSticker = db.CheckSticker( Attachment )

		# Если стикер не найден в БД
		if GetSticker is None:
			StickerURL = 'https://api.telegram.org/file/bot{0}/{1}'.format( config.getCell( 'telegram_token' ), Attachment )
			SaveSticker( StickerURL, Attachment )
			GetSticker = db.CheckSticker( Attachment )

		#print( GetSticker )

		try:
			module.vk.messages.send( chat_id = config.getCell( 't_' + chatid ), message = "", attachment = GetSticker, random_id=randid )
		except vk_api.ApiError as error_msg:
			module.vk.messages.send( user_id = config.getCell( 't_' + chatid ), message = "", attachment = GetSticker, random_id=randid )

	return False

def CheckRedirect_telegram( chatid, text, fromUser, Attachment ):
	if not config.getCell( 't_' + chatid ) is None:
		TransferMessageToVK( chatid, text, fromUser, Attachment )
		return False

# Посылаем простые сообщения в Telegram
# Идея: сделать в будущем наклонные столбики, теперь главное не забыть
def TransferMessagesToTelegram( idd, UserName, mbody, FwdList ):

	# Условие выполняется в случае какого-либо события
	if UserName is None:
		module.bot.send_message( config.getCell( 'vk_' + idd ), str( mbody ) )
		return False

	time = current_time()
	NiceText = str( time + ' | ' + UserName + ': ' + mbody )

	if not FwdList is None:

		ForwardText = ''

		for f in FwdList[0:]:
			ForwardText = ForwardText + str( ' | ' + f.get( 'UserName' ) + ':' + ' ' + f.get( 'body' ) + ' \n\n' )

		module.bot.send_message( config.getCell( 'vk_' + idd ), NiceText + '\n\n' + ForwardText )

	else:
		module.bot.send_message( config.getCell( 'vk_' + idd ), NiceText )

# Посылаем аттачменты в Telegram
def TransferAttachmentsToTelegram ( idd, attachments ):

	for j in attachments[0:]:

		AttType = j.get( 'type' )
		Link = j.get( 'link' )

		if AttType == 'photo' or AttType == 'sticker':
			module.bot.send_photo( config.getCell( 'vk_' + idd ), Link )

		elif AttType == 'doc' or AttType == 'gif' or AttType == 'audio':
			module.bot.send_document( config.getCell( 'vk_' + idd ), Link )

		elif AttType == 'file':
			module.bot.send_message( config.getCell( 'vk_' + idd ), Link )

		elif AttType == 'video':

			# Потому что в ВК не может отправить полную ссылку на файл видео -_-
			module.bot.send_message( config.getCell( 'vk_' + idd ), Link )

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

			CheckRedirect_vk( rawMessages )

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

			CheckRedirect_telegram( str( m.chat.id ), str( m.text ), GetUserTName(m.from_user), None )

		elif m.content_type == 'sticker':

			if not ( config.getCell('vk_EnableStickers') ):
				return False

			FilePath = module.bot.get_file( m.sticker.file_id ).file_path

			CheckRedirect_telegram( str( m.chat.id ), str( m.text ), GetUserTName(m.from_user), str( FilePath ) )


def init_telegram():

	module.bot = telebot.TeleBot( config.getCell( 'telegram_token' ) )
	print( "Successfully loginned in telegram!")
	input_telegram()

def input_telegram():

	if ( config.getCell('telegram_useProxy') ):
		Proxy_type = str( config.getCell('p_type') )
		Proxy_UserInfo = str( config.getCell('p_user') + ':' + config.getCell('p_password') )
		Proxy_Data = str( config.getCell('p_host') + ':' + config.getCell('p_port') )
		telebot.apihelper.proxy = { 
		'http': '%s://%s@%s' % ( Proxy_type, Proxy_UserInfo, Proxy_Data ),
		'https': '%s://%s@%s' % ( Proxy_type, Proxy_UserInfo, Proxy_Data )
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
def AddStickerIntoVK( path, Sticker ):

	StickerList = []
	OurFile = path + Sticker

	upload = vk_api.VkUpload( vk_session )
	photo = upload.photo( OurFile + ".png", album_id = config.getCell( 'vk_album_id' ) )

	if ( config.getCell('vk_detelestickers') ):
		os.remove( OurFile + ".png" )

	OurVK = 'photo{}_{}'.format( photo[0]['owner_id'], photo[0]['id'] )

	StickerList.append( { 'sticker_t':OurFile,
						  'sticker_vk':OurVK } )

	return StickerList

def SaveSticker( StickerURL, Attachment ):

	Attachment = Attachment.split('/')

	content = ur.urlopen( StickerURL ).read()

	path = Attachment[0] + '/'
	if not os.path.exists( path ):
		os.makedirs( path )

	# Перекодирование из webp в png

	ImageWebp = path + Attachment[1]

	out = open( ImageWebp, 'wb' )
	out.write( content )
	out.close()

	img = Image.open(ImageWebp)

	if ( config.getCell('vk_sticker_EnableScale') ):
		scale = config.getCell( 'vk_sticker_size' )
		img.thumbnail((scale, scale))
	img.save( ImageWebp + ".png", "PNG")
	os.remove( ImageWebp )

	#print( 'Sticker saved!' )

	Stickers = AddStickerIntoVK( path, Attachment[1] )
	db.AddStickerIntoDb( Stickers )

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