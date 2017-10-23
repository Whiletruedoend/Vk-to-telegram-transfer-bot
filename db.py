#!/usr/bin/env python3.4
import sqlite3 # Стандартная либа насколько я помню
import os

# Если стикеры не найдены, то добавляем их в бд
def AddStickerIntoDb( Stickers ):

	conn = sqlite3.connect('bot.db')
	c = conn.cursor()

	c.execute("INSERT INTO stickers VALUES ( '" + Stickers[0].get('sticker_t') + "' , '" + Stickers[0].get('sticker_vk') + "')")

	conn.commit()
	conn.close()

# Создаём новую базу данных
def CreateDb():

	conn = sqlite3.connect('bot.db')
	c = conn.cursor()

	c.execute('''CREATE TABLE stickers
             (telegram_sticker text, vk_sticker text)''')

	conn.commit()
	conn.close()

# Проверяем стикер на наличие в БД
def CheckSticker( Attachment ):

	if not os.path.isfile( './bot.db' ):
		print( 'База данных не найдена, создаём новую...' )
		CreateDb()

	conn = sqlite3.connect('bot.db')
	c = conn.cursor()

	sql = """SELECT * FROM stickers"""

	CheckRow = c.execute( sql )

	data = c.fetchall()

	for rec in data:

		telegram, vk = rec

		if str( telegram ) == str( Attachment ):
			#print( 'Стикер найден!' )
			return vk

	#print( 'Ничего не найдено!' )
	return None

	conn.commit()
	conn.close()