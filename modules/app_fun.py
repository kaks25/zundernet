
import os

import sys, multiprocessing, time

import datetime

import subprocess
import json
import psutil
import threading
import modules.aes as aes

def check_deamon_running():

	is_komodod_running=False
	tmppid=-1
	
	for proc in psutil.process_iter(): 
		try:
			# Get process name & pid from process object.
			processName = proc.name()
			processID = proc.pid
			procstr=''.join(proc.cmdline())
			if 'komodod' in procstr and '-ac_name=PIRATE' in procstr: #==deamon_cmd: 
				zxc=proc.as_dict(attrs=['pid', 'memory_percent', 'name', 'cpu_times', 'create_time', 'memory_info', 'cmdline','cwd'])
				
				is_komodod_running=True
				tmppid=zxc['pid']
				break
					
		except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
			x=1
			
	return is_komodod_running, tmppid	

	
def split_memo( tmpmemo,sign_as_hash=True):
	cry=aes.Crypto(224) 
	
	tmpmemo=tmpmemo.replace('@zUnderNet','')
	splmemo=tmpmemo.split('\n')
	# print('app fun replace ',tmpmemo)
	
	tmpsign=splmemo[-1]
	tmpsign_spl=tmpsign.split(';')

	sign1='none'
	sign1_n=-1
	sign2='none'
	sign2_n=-1
	tmpmsg=tmpmemo
	
	if len(splmemo)==1:
		tmpmsg=tmpmsg.strip()
		return tmpmsg,sign1,sign1_n,sign2,sign2_n #,sign_r
		
	
	if len(tmpsign_spl)<4: # and len(tmpsign)<40 :
		tmpmsg='\n'.join(splmemo[:-1])
		sign1=tmpsign_spl[0] #cry.utf8_1b2hash(tmpsign_spl[0])
		sign1_n=cry.utf8_1b_to_int(tmpsign_spl[1])
		
	else: #if len(tmpsign_spl)==4: # and len(tmpsign)<80: # on change sign1_n=1
		tmpmsg='\n'.join(splmemo[:-1])
		sign1=tmpsign_spl[0] #cry.utf8_1b2hash(tmpsign_spl[0])
		sign1_n=cry.utf8_1b_to_int(tmpsign_spl[1])
		sign2=tmpsign_spl[2] #cry.utf8_1b2hash(tmpsign_spl[2])
		sign2_n=cry.utf8_1b_to_int(tmpsign_spl[3])
		
	if sign_as_hash:
		sign1= cry.utf8_1b2hash(sign1)
		if sign2!='none':
			sign2= cry.utf8_1b2hash(sign2)
	
		
	tmpmsg=tmpmsg.strip()
		
	return tmpmsg,sign1,sign1_n,sign2,sign2_n #,sign_r
	


	
	

def run_process( CLI_STR,cmd):
	
	if type(cmd)!=type([]):
		cmdtmp=cmd.split()
		cmd=[cmdii for cmdii in cmdtmp]
		
	zxc=subprocess.run(CLI_STR+cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
	
	return zxc.stdout.decode('utf-8') 

def json_to_str(dd,tt=''):	

	if type(dd)==type('asd'):
		return dd
		
	tmp=''
	nextt=tt+'\t'
	if type(dd)==type([]):
		for d in dd:
			if tt=='':
				nextt=''
			x=json_to_str(d,nextt)
			tmp+=tt+ x +'\n'
	else:
		for k,v in dd.items():
			if type(v)==type([]):
				tmp+=tt+str(k)+':\n'
				for d in v:
					y=json_to_str(d,nextt)
					tmp+=y #+'\n'
			else:
				tmp+=tt+str(k)+': '+str(v)+'\n'

	return tmp
	
	

# https://stackoverflow.com/questions/17455300/python-securely-remove-file
def secure_delete(path, passes=5): #app_fun.secure_delete(self.tmp_err)
	with open(path, "ba+") as delfile:
		length = delfile.tell()
		for ii in range(passes):
			delfile.seek(0)
			delfile.write(os.urandom(length))
	os.remove(path)




class CompactCharInt89:  # excluded |`;\

	def __init__(self):
		
		self.ascii_chain="!#$%&'()*+,-./0123456789:<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[]^_abcdefghijklmnopqrstuvwxyz{}~"
		self.ascii_arr=list(self.ascii_chain) 
		
		self.llen=len(self.ascii_arr)
	
	def encode(self,intnum):
		
		retv=''
		while True:
			jj=intnum%self.llen
			retv=retv+self.ascii_arr[jj]
			intnum=int(intnum/self.llen)
			if intnum==0:
				return retv
			
	def decode(self,sstr):
		
		retv=0
		pp=1
		for ss in sstr:
			
			retv+=self.ascii_arr.index(ss)*pp
			pp=pp*self.llen
			
		return retv
		

		
		
	
class TmpFilesOE:
	
	def __init__(self):
	
		if not os.path.exists('logs'):
			os.mkdir('logs')
	
		tmp_time=now_to_str()
		self.tmp_output=os.path.join('logs','o_'+tmp_time+'.tmp')
		self.tmp_err=os.path.join('logs','e_'+tmp_time+'.tmp')

	def get_files_names(self):
		return self.tmp_output, self.tmp_err
		
	def get_files(self,mmode):
		fo=open(self.tmp_output,mmode)
		fe=open(self.tmp_err,mmode)
		
		return fo, fe
		
	def get_files_content(self):
		f1,f2=self.get_files('r')
		v1=f1.read()
		v2=f2.read()
		self.close_files(f1,f2)
		
		return v1,v2
		
	def close_files(self,fo,fe):
		fo.close()
		fe.close()
		
		
	def delete_files(self):
		if hasattr(self,'tmp_output') and hasattr(self,'tmp_err'):
			if os.path.exists(self.tmp_output):
				
				secure_delete(self.tmp_output)
				
			if os.path.exists(self.tmp_err):
				
				secure_delete(self.tmp_err)


def now_to_timestamp():
	return datetime.datetime.now().timestamp()


def timestamp_to_datetime(ts,ret_str=False):
	
	dtts=datetime.datetime.fromtimestamp(ts)
	if ret_str:
		sdt=str(dtts)
		sdt=sdt.split('.')
		return sdt[0]
	else:
		return dtts
	
	
def now_to_str(short=True,ret_timestamp=False): #,correct=0

	tmpnow=datetime.datetime.now()
	sdt=str(datetime.datetime.now())
	if short:
		sdt=sdt.replace('-','').replace(' ','_').replace(':','_')
	sdt=sdt.split('.')
	
	if ret_timestamp:
		ts=tmpnow.timestamp()
		return sdt[0], ts
	
	return sdt[0]

def datetime_from_str(str1):
	return datetime.datetime.strptime(str1,'%Y-%m-%d %H:%M:%S')
	
def date2str(ddate):
	sdt=str(ddate)
	sdt=sdt.split('.')
	return sdt[0]

def today_add_days(ddays):
	tmpnow=datetime.datetime.now()+datetime.timedelta(days=ddays)
	return date2str(tmpnow)

def printsleep(sleep_time,print_char='.'):

	while sleep_time>0:
		time.sleep(1)
		sleep_time=sleep_time-1
		if sleep_time%2==0:
			print(print_char,end='', flush=True)
			
			
			

def check_already_running(main_script_name): # takes about 2sec to check on win 10 ... 

	script_counts=0
	
	for proc in psutil.process_iter(attrs=[  'cmdline','name' ]):
		# toti+=1
		try:
		# if True:
			# Get process name & pid from process object.
			processName = proc.info['name'] #()
			
			if 'python' in processName :
				
				zxc=str(proc.info['cmdline']  )
				
				if main_script_name in zxc: #==zxc[-1]: #  #str(zxc['cmdline']):
					
					script_counts+=1
					
		except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
			pass

			
	if script_counts>1:
		print('\n\n__ '+main_script_name+' ALREADY RUNNING __\n\n')
		exit()
		

		
		
def proces_return_oe(oo,ee):

	if ee!='':
		return ee
		
	if oo=='':
		return 'Done'
		
	return oo
	
