#!/usr/bin/python3
import asyncio
from aiohttp import web
import pandas as pd
from deeppavlov import build_model, configs
from urllib.parse import unquote
import subprocess

WEBHOOK_PORT = 8081
WEBHOOK_LISTEN = '0.0.0.0'  # In some VPS you may need to put here the IP addr

async def call_test(request):
	return web.Response(text='ok',content_type="text/html")

async def call_talk(request):
	with open('/mnt/storage/share/alex/projects/deeppavlov_rugpt3/job.txt','r') as f:
		active = f.read().replace('\n', '')
		f.close()
	print(active)
	if active=='1':
		answer = 'Занят, подожди..'
	else:
		with open('/mnt/storage/share/alex/projects/deeppavlov_rugpt3/job.txt','w') as f:
			f.write('1')
			f.close()
		
		# disable miner ++			
		#sudo systemctl stop miner
		MyOut = subprocess.Popen(
			['systemctl', 'stop', 'miner_0'],
			stdout=subprocess.PIPE, 
			stderr=subprocess.STDOUT
		)
		stdout,stderr = MyOut.communicate()
		print('disable miner', stdout.decode("utf-8"))
		# disable miner --
		
		# main ++	
		answer = ''
		group_id	= unquote( request.rel_url.query['group_id'	] )
		user_id		= unquote( request.rel_url.query['user_id'	] )
		question	= unquote( request.rel_url.query['question'	] )
		print('group_id:',group_id)
		print('user_id:',user_id)
		print('question:',question)
		df = pd.read_csv('/mnt/storage/share/alex/projects/deeppavlov_rugpt3/data.csv')
		# select phrases
		pre_words = question.replace("?","").split(" ")
		words =[]
		for word in pre_words:
			if len(word)>2:
				words.append(word)    
		if len(words)==0:
			answer = 'Слишком короткий запрос'    

		df = df[df.text.str.contains('|'.join(words), regex = True)]

		if len(words)==0:
			answer = 'В этом вопросе мало слов'

		if answer =='':
			
			data = df.text.values.tolist()

			answers = pd.DataFrame(columns=['answer','score'])
			for theme in data:
				res = model([theme], [question])
				answers = answers.append({'answer':res[0][0], 'score':res[2][0]}, ignore_index=True)            

			max_score = answers.score.max()    
			if len(answers)==0:
				answer = 'Какая то ошибка в коде'
			else:
				answer = answers[answers.score==max_score].iloc[0].answer
		# main --
		
		# enable miner ++			
		#sudo systemctl stop miner
		MyOut = subprocess.Popen(
			['systemctl', 'start', 'miner_0'],
			stdout=subprocess.PIPE, 
			stderr=subprocess.STDOUT
		)
		stdout,stderr = MyOut.communicate()
		print('enable miner', stdout.decode("utf-8"))
		# enable miner --
		
		with open('/mnt/storage/share/alex/projects/deeppavlov_rugpt3/job.txt','w') as f:
			f.write('0')
			f.close()
	print('answer:',answer)
	return web.Response(text=answer,content_type="text/html")

model = build_model(configs.squad.squad_ru_rubert_infer, download=False)

app = web.Application()
app.router.add_route('GET', '/test', call_test)
app.router.add_route('GET', '/talk', call_talk)

web.run_app(
    app,
    host=WEBHOOK_LISTEN,
    port=WEBHOOK_PORT,
)