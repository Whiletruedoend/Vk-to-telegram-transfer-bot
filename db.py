# -*- coding: utf-8 -*-
import sqlite3 # Стандартная либа насколько я помню
import os

# Если стикеры не найдены, то добавляем их в бд
def addStickerIntoDb( stickers ):

	conn = sqlite3.connect('bot.db')
	c = conn.cursor()

	c.execute("INSERT INTO stickers VALUES ( '" + stickers[0].get('sticker_t') + "' , '" + stickers[0].get('sticker_vk') + "')")

	conn.commit()
	conn.close()

# Создаём новую базу данных
def createDb():

	conn = sqlite3.connect('bot.db')
	c = conn.cursor()

	c.execute('''CREATE TABLE stickers
             (telegram_sticker text, vk_sticker text)''')

	conn.commit()
	conn.close()

# Проверяем стикер на наличие в БД
def checkSticker( attachment ):

	if not os.path.isfile( './bot.db' ):
		print( 'База данных не найдена, создаём новую...' )
		createDb()

	conn = sqlite3.connect('bot.db')
	c = conn.cursor()

	sql = """SELECT * FROM stickers"""

	CheckRow = c.execute( sql )

	data = c.fetchall()

	for rec in data:

		telegram, vk = rec

		if str( telegram ) == str( attachment ):
			#print( 'Стикер найден!' )
			return vk

	#print( 'Ничего не найдено!' )
	return None

	conn.commit()
	conn.close()