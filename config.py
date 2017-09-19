import sys

module = sys.modules[__name__]

def setCell( name, value ):
	module.table[name] = value

def getCell( name ):
	return module.table.get( name )

def initConfig():
	module.table = {}

	#setCell( "api_key", '') # API ключ для конвертации стикеров ( Пока что недоделано! )
	setCell( "vk_msgForPick", 2 ) # Сколько сообщений за раз обрабатывать? Просто не трогай...

	setCell( "vk_AddFriends", 1 ) # Автоматически добавлять новых пользователей в друзья?
	# P.S. Функция добавления активируется при написании на аккаунт ВК любого сообщения

	setCell( "vk_login", "+88005553535" ) # Логин от аккаунта ВК
	setCell( "vk_password", "Password" ) # Пароль от аккаунта ВК

	setCell( "telegram_token", "12345678:ABcDeFgHeVzS-6543-dWEdGAJ1234" ) # Токен ботинка в Telegram

	###############

	setCell( "vk_1", '-249416176' ) # Пример переадресации из чата ВК в Telegram
	setCell( "t_-249416176", '1' ) # Пример переадресации из чата ВК в Telegram
	# P.S. В нашем случае 1 - 'локальный' ID чата для аккаунта ВК

	setCell( "vk_417110104", '-236472090' ) # Пример переадресации ЛС ВК в Telegram
	setCell( "t_-236472090", '417110104' ) # Пример переадресации ЛС ВК в Telegram

	#setCell( "vk_", '-' ) # Шаблон
	#setCell( "t_-", '' ) # Шаблон