#!/usr/bin/python3
import asyncio
from aiohttp import web
import pandas as pd
from deeppavlov import build_model, configs
from urllib.parse import unquote
import subprocess
import os.path

WEBHOOK_PORT = 8081
WEBHOOK_LISTEN = '0.0.0.0'  # In some VPS you may need to put here the IP addr

async def call_test(request):
	return web.Response(text='ok',content_type="text/html")

def mark_job_complete():
	with open('/mnt/storage/share/alex/projects/deeppavlov_rugpt3/job.txt','w') as f:
		f.write('0')
		f.close()

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
		
		# main ++	
		answer = ''
		group_id	= unquote( request.rel_url.query['group_id'	] )
		user_id		= unquote( request.rel_url.query['user_id'	] )
		question	= unquote( request.rel_url.query['question'	] )
		print('group_id:',group_id)
		print('user_id:',user_id)
		print('question:',question)
		
		if '/set ' in question:
			df = pd.read_csv('/mnt/storage/share/alex/projects/deeppavlov_rugpt3/data/settings.csv')
			set_group = question.replace('/set ','').split(' ')[0]
			set_user = question.replace('/set ','').split(' ')[1]			
			#df = pd.DataFrame(columns=['master','group','user']) # master: user or group in which the rules apply			
			if os.path.isfile('data/'+set_group+'.csv'):
				df = df.append({'master':user_id,'group':set_group,'user':set_user}, ignore_index=True)
				answer+= 'group '+set_group+' was set'
			else:
				answer+= 'group '+set_group+' not found in my db'		
			mark_job_complete()
			return web.Response(text=answer,content_type="text/html")
		
		# load relation from settings
		settings = pd.read_csv('data/settings.csv')
		#mask = ( settings['master'] == str(group_id)) | (settings['master'] == str(user_id) )
		#settings = settings[mask]
		settings = settings[settings.master==int(group_id)]
		if len(settings)==0:
			answer+= 'master '+group_id+' not found in my db'
			mark_job_complete()
			return web.Response(text=answer,content_type="text/html")
		
		data_file_name = settings.iloc[0].group
		
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
		
		df = pd.read_csv('/mnt/storage/share/alex/projects/deeppavlov_rugpt3/data/'+str(data_file_name)+'.csv')
		if not settings.iloc[0].user == 'all':
			df = df[df.from_id==int(settings.iloc[0].user)]
			
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

			answers = pd.DataFrame(columns=['answer','quote','score'])
			for quote in data:
				res = model([quote], [question])
				answers = answers.append({'answer':res[0][0], 'quote':quote, 'score':res[2][0]}, ignore_index=True)            

			max_score = answers.score.max()    
			if len(answers)==0:
				answer = 'Я ограничен в ответах'
			else:
				top_row = answers[answers.score==max_score].iloc[0]
				answer = top_row.answer+'. '+top_row.quote
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
		
		mark_job_complete()
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