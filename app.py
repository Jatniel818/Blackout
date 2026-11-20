import json, os, urllib.request, urllib.error, socket
from pathlib import Path
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
BASE=Path(__file__).resolve().parent
MODEL=os.getenv('OLLAMA_MODEL','qwen2.5:3b')
class Handler(SimpleHTTPRequestHandler):
 def __init__(self,*args,**kwargs):super().__init__(*args,directory=str(BASE/'static'),**kwargs)
 def reply(self,data,status=200):
  body=json.dumps(data).encode();self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
 def do_POST(self):
  if self.path!='/api/chat':return self.reply({'error':'Not found'},404)
  try:
   n=int(self.headers.get('Content-Length','0'))
   if not 0<n<=64000:return self.reply({'error':'Conversation too large. Start a new chat.'},400)
   data=json.loads(self.rfile.read(n));messages=data.get('messages') if isinstance(data,dict) else None
   if not isinstance(messages,list) or not 1<=len(messages)<=20:return self.reply({'error':'Send between 1 and 20 messages.'},400)
   for i,m in enumerate(messages):
    if not isinstance(m,dict) or m.get('role')!=('user' if i%2==0 else 'assistant') or not isinstance(m.get('content'),str) or not m['content'].strip() or len(m['content'])>8000:return self.reply({'error':'Invalid conversation.'},400)
   if messages[-1]['role']!='user':return self.reply({'error':'End with a question.'},400)
   payload={'model':MODEL,'stream':False,'messages':[{'role':'system','content':'You are Blackout, a local knowledge assistant designed for communities when outside networks and cloud services are unavailable. Help explain concepts, reason through plans using information the user supplies, and troubleshoot equipment. Answer clearly and concisely. Be honest about uncertainty. You have no live internet, sensors, local resource directory, or tools. Never imply that you can monitor outages or verify current conditions. Do not invent current locations, supplies, availability, or emergency information. Do not roleplay a real disaster unless explicitly asked; the application is a dystopian-themed prototype.'}]+[{'role':m['role'],'content':m['content']} for m in messages],'options':{'temperature':0.4,'num_predict':600,'num_ctx':4096}}
   request=urllib.request.Request(os.getenv('OLLAMA_URL','http://127.0.0.1:11434').rstrip('/')+'/api/chat',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
   try:
    with urllib.request.urlopen(request,timeout=180) as r:result=json.load(r)
    answer=result['message']['content']
    if not isinstance(answer,str) or not answer.strip():raise ValueError()
    return self.reply({'answer':answer,'model':MODEL})
   except urllib.error.HTTPError as e:
    return self.reply({'error':f'Ollama returned HTTP {e.code}. Check that {MODEL} is installed.'},502)
   except (TimeoutError,socket.timeout):return self.reply({'error':'The model took too long. Try a shorter question.'},504)
   except (OSError,ValueError,KeyError,TypeError):return self.reply({'error':'Could not get a response from local Ollama. Check the service and connection.'},502)
  except (ValueError,TypeError):return self.reply({'error':'Invalid request.'},400)
if __name__=='__main__':ThreadingHTTPServer((os.getenv('BIND_HOST','127.0.0.1'),int(os.getenv('PORT','8787'))),Handler).serve_forever()
