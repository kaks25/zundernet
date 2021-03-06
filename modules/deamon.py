import os
import time
import getpass

import sys
import psutil

import datetime

import subprocess
import json
import modules.app_fun as app_fun
import modules.wallet_api as wallet_api
import modules.localdb as localdb
import modules.aes as aes
import modules.flexitable	 as flexitable
	

	
	
class DeamonInit:


	def update_wallet(self,*args): # syntetic args passed auto by elem
		
		idb=localdb.DB()
		if self.started:
			utxo_change=self.the_wallet.refresh_wallet()
			
			if True: #utxo_change>0:
				# print('refreshing wallet')
				disp_dict=self.the_wallet.display_wallet() #sorting , rounding 
				# print('refreshing wallet 33')
				date_str=app_fun.now_to_str(False)
				table={}
				table['jsons']=[{'json_name':"display_wallet", 'json_content':json.dumps(disp_dict), 'last_update_date_time':date_str}]
				idb.upsert(table,['json_name','json_content','last_update_date_time'],{'json_name':['=',"'display_wallet'"]})
				
				# print('refreshing wallet 39')
				while self.wallet_display_set.is_locked():
					time.sleep(1)
					
				self.wallet_display_set.lock_basic_frames()
				# print('refreshing wallet 44')
				grid_lol_wallet_sum=self.wallet_display_set.prepare_summary_frame()
				self.wallet_summary_frame.update_frame(grid_lol_wallet_sum)
				
				grid_lol3=self.wallet_display_set.prepare_byaddr_frame()

				if len(grid_lol3)>0:
					self.wallet_details.update_frame(grid_lol3)
			
				self.wallet_display_set.unlock_basic_frames()
				
				self.notifications.update_notif_frame()
				# print('update mesages??? / deamon')
				self.messages.update_msgs()
			
			
			# self.tx_history.update_history_frame()
			# self.task_history.update_history_frame()
		
		
	def init_clear_queue(self):	
		idb=localdb.DB()
		waiting=idb.select('queue_waiting', ["type","wait_seconds","created_time","command","json","id","status"])
		
		for ii,rr in enumerate(waiting):

			if rr[6]=='processing': # and len(idb.select('queue_done',['id'],{'id':['=',rr[5]]} ) )>0:
				table={}
				table['queue_done']=[{"type":rr[0],"wait_seconds":rr[1],"created_time":rr[2],"command":rr[3],"json":rr[4],"id":rr[5],"result":'old - forced failed on app init','end_time':app_fun.now_to_str(False)}]
				
				idb.insert(table,["type","wait_seconds","created_time","command","json","id","result",'end_time'])
				idb.delete_where('queue_waiting',{'id':['=',rr[5] ]})

	
	def process_queue(self):
		idb=localdb.DB()
		cc=aes.Crypto()		

		gitmp=app_fun.run_process(self.cli_cmd,'getinfo')
		
		y=json.loads(gitmp)
		notar=y["notarized"]
		
		tmpwhere={'Type':['=',"'out'"],'Category':['=',"'send'"],'status':['=',"'sent'"],'block':['<',notar] }
		toupdate=idb.select('tx_history', ["txid",'date_time'],tmpwhere,distinct=True)

		if len(toupdate)>0:
		
			for tt in toupdate:
				txidok=self.the_wallet.z_viewtransaction( tt[0] ) # if not in blocks anymore ? not valid ?
				
				tmpwhere2={'Type':['=',"'out'"],'Category':['=',"'send'"],'status':['=',"'sent'"],'block':['<',notar], 'txid':['=',"'"+tt[0]+"'"] }
				
				if txidok=='not valid txid' and datetime.datetime.now()>app_fun.datetime_from_str(tt[1])+datetime.timedelta(hours=1):
		
					table={}
					table['tx_history']=[{'status':'reorged'}]
					idb.update( table,['status'],tmpwhere2)
					# update notification
					wwhere={'details':['=','"'+tt[0]+'"'] }
					table={}
					table['notifications']=[{'status':'reorged', 'closed':'False' }]
					idb.update( table,['status', 'closed'],wwhere)
					
					# also update msg table: 
					table={}
					table['msgs_inout']=[{'tx_status':'reorged'}] #, 'txid':''
					idb.update( table,['tx_status'  ], {'txid':['=', tt[0] ],'type':['=','sent']})
					
				elif txidok!='not valid txid':
				
					table={}
					table['tx_history']=[{'status':'notarized'}]
					idb.update( table,['status'],tmpwhere2)
					# update notification
					wwhere={'details':['=','"'+tt[0]+'"'] }
					table={}
					table['notifications']=[{'status':'notarized' }]
					idb.update( table,['status'],wwhere)
					# also update msg table: 
					table={}
					table['msgs_inout']=[{'tx_status':'notarized' }]
					idb.update( table,['tx_status'  ], {'txid':['=',  tt[0] ],'type':['=','sent']})
					
					
					
			self.tx_history.update_history_frame()
		# except:
			# pass
		
		
		waiting=idb.select('queue_waiting', ["type","wait_seconds","created_time","command","json","id","status"])
		
		merged_ii=[]
		for ii,rr in enumerate(waiting):
		
			if ii in merged_ii:
				continue
			
			if rr[6] =='done':
				
				task_done=idb.select('queue_done', ['end_time','result'],{'id':['=',rr[5]]})
				
				if len(task_done)>0:
					time_since_end=(datetime.datetime.now()-app_fun.datetime_from_str(task_done[0][0]) ).total_seconds()
					
					if rr[1]>=900 and time_since_end>=600 or rr[1]<900 and time_since_end>=3*60:
						idb.delete_where('queue_waiting',{'id':['=',rr[5] ] })
				else:
					table={}
					table['queue_done']=[{"type":rr[0],"wait_seconds":rr[1],"created_time":rr[2],"command":rr[3],"json":rr[4],"id":rr[5],"result":'unknown','end_time':app_fun.now_to_str(False)}]
					idb.insert(table,["type","wait_seconds","created_time","command","json","id","result",'end_time'])
				
				continue
			
			if rr[6] not in ['waiting','awaiting_balance']:
				continue
			
			if rr[1] - (datetime.datetime.now()-app_fun.datetime_from_str(rr[2]) ).total_seconds() - 1 >0:
				continue
			
			# 1 change status in case of task takes longer
			if rr[6]=='waiting':
				table={}
				table['queue_waiting']=[{'status':'processing'}]
				idb.update( table,['status'],{'id':[ '=',rr[5] ]})
			
				grid_lol4=self.wallet_display_set.prepare_queue_frame()
				self.queue_status.update_frame(grid_lol4)
				
				self.wallet_display_set.queue_frame_buttons( grid_lol4,self.queue_status)
				time.sleep(1)
				
			if rr[3]=='import_view_key': #json.dumps({'addr':tmpaddr,'viewkey':tmpvk})
				adrvk=json.loads(rr[4])
				tmpresult=self.the_wallet.imp_view_key( adrvk['addr'],adrvk['viewkey'] )
				table={}
				table['queue_done']=[{"type":rr[0],"wait_seconds":rr[1],"created_time":rr[2],"command":rr[3],"json":rr[4],"id":rr[5],"result":tmpresult,'end_time':app_fun.now_to_str(False)}]
				
				idb.insert(table,["type","wait_seconds","created_time","command","json","id","result",'end_time'])
				
				
			elif rr[3]=='validate_addr':
				adrvk=json.loads(rr[4])
				tmpresult=self.the_wallet.validate_zaddr( adrvk['addr'] )
				table={}
				table['queue_done']=[{"type":rr[0],"wait_seconds":rr[1],"created_time":rr[2],"command":rr[3],"json":rr[4],"id":rr[5],"result":tmpresult,'end_time':app_fun.now_to_str(False)}]
				
				idb.insert(table,["type","wait_seconds","created_time","command","json","id","result",'end_time'])
				
				table={}
				if tmpresult=='not valid exception' or tmpresult==False:
					
					table['addr_book']=[{ 'addr_verif':-1 }]  #,'viewkey_verif' 
				else:
					table['addr_book']=[{ 'addr_verif':1 }]  #,'viewkey_verif' 
				idb.update(table,[  'addr_verif'],{'Address':['=',"'"+adrvk['addr']+"'"]})
			
			elif rr[3]=='new_addr':
			
				# 2 create results / wallet api
				tmpresult=self.the_wallet.new_zaddr()
				
				# 3 insert result to queue done
				table={}
				table['queue_done']=[{"type":rr[0],"wait_seconds":rr[1],"created_time":rr[2],"command":rr[3],"json":rr[4],"id":rr[5],"result":tmpresult,'end_time':app_fun.now_to_str(False)}]
				
				idb.insert(table,["type","wait_seconds","created_time","command","json","id","result",'end_time'])
				
				
			elif rr[3]=='export_wallet':
						
				tmpresult=self.the_wallet.export_wallet()
				
				path2=json.loads(rr[4])
				path2=path2['path']+'/'+'addrkeys_'+app_fun.now_to_str(True)+'.txt'
				if self.wallet_display_set.password!=None:
					if flexitable.msg_yes_no("Encrypt exported wallet with your password?", "If you make a backup for yourself 'yes' is good option. If you share or sell the wallet better select 'no' since sharing personal passwords is not good practice."):
						cc.aes_encrypt_file( json.dumps(tmpresult),path2 ,self.wallet_display_set.password)
					elif flexitable.msg_yes_no("Encrypt exported wallet with new password?", "Encrypt exported wallet with new password? Only hit 'no' if you really do not need encryption for this export."):
						cc.aes_encrypt_file( json.dumps(tmpresult),path2 ,cc.rand_password(32))
					else:
						cc.write_file(path2 ,json.dumps(tmpresult))
				else:
					cc.write_file(path2 ,json.dumps(tmpresult))
				
				table={}
				table['queue_done']=[{"type":rr[0],"wait_seconds":rr[1],"created_time":rr[2],"command":rr[3],"json":rr[4],"id":rr[5],"result":'exported to '+path2,'end_time':app_fun.now_to_str(False)}]
				
				idb.insert(table,["type","wait_seconds","created_time","command","json","id","result",'end_time'])
				

			elif rr[3]=='export_viewkey':
				ddict=json.loads(rr[4])
				# print('\n\n\nexporting view key',ddict)
				tmpresult=self.the_wallet.exp_view_key(ddict['addr'])
				
				pto='screen'
				if ddict['password']=='':
					flexitable.output_copy_input('View key display' ,'Address  '+ddict['addr']+'\n\nView key '+tmpresult)
					
				else:
					
					tmppass=cc.rand_password(32)
					tmpresult=json.dumps({'addr':ddict['addr'], 'viewkey':tmpresult})
					pto=ddict['path']+'/viewkey_'+app_fun.now_to_str()+'.txt'
					cc.aes_encrypt_file( tmpresult, pto  , tmppass) 
					flexitable.output_copy_input('Password for file exported to '+pto,tmppass)
									
				table={}
				table['queue_done']=[{"type":rr[0],"wait_seconds":rr[1],"created_time":rr[2],"command":rr[3],"json":rr[4],"id":rr[5],"result":'exported to '+pto,'end_time':app_fun.now_to_str(False)}]
				
				idb.insert(table,["type","wait_seconds","created_time","command","json","id","result",'end_time'])
			
			elif rr[3]=='show_bills': # 
				ddict=json.loads(rr[4])
				tmpresult={}
				if ddict['addr'] in self.the_wallet.all_unspent:
					tmpresult2=self.the_wallet.all_unspent[ddict['addr']] 
					for ii,dd in tmpresult2.items():
						tmpresult[ii]={ 'amount':dd['amount'], 'conf':dd['conf']}
						
				table={}
				table['queue_done']=[{"type":rr[0],"wait_seconds":rr[1],"created_time":rr[2],"command":rr[3],"json":rr[4],"id":rr[5],"result":json.dumps(tmpresult),'end_time':app_fun.now_to_str(False)}]
				
				idb.insert(table,["type","wait_seconds","created_time","command","json","id","result",'end_time'])
				
			elif rr[3]=='send': # 
			
				def insert_notification(details, tmpjson):
					if type(tmpjson)==type({}):
						tmpjson=json.dumps(tmpjson)
				
					idb=localdb.DB()
					table={}
					dt,ts=app_fun.now_to_str(False,ret_timestamp=True)
					table['notifications']=[{'opname':'send','datetime':dt,'status':'Failed','details':details,'closed':'False','orig_json':tmpjson,'uid':'auto'}]
					
					idb.insert(table,['opname','datetime','status','details', 'closed','orig_json' ,'uid'])
				
			
				ddict=json.loads(rr[4])
				exceptions=[]
				total_conf_per_addr=self.wallet_display_set.amount_per_address[ddict['fromaddr']]
				
				sum_cur_spending=0
					
				if ddict['fromaddr'] in self.wallet_display_set.amount_per_address :
					for tt in ddict['to']:
						sum_cur_spending+=float(tt['a'])
				
				if sum_cur_spending>total_conf_per_addr-0.0001: # validate amoaunt to send
					#
				
					table={}
					table['queue_waiting']=[{'status':'awaiting_balance'}]
					idb.update( table,['status'],{'id':[ '=',rr[5] ]}) # 
				
				elif self.the_wallet.validate_zaddr(ddict['fromaddr']) : # first validate addr:
				
					table={}
					table['queue_waiting']=[{'status':'processing'}]
					idb.update( table,['status'],{'id':[ '=',rr[5] ]})
				
					grid_lol4=self.wallet_display_set.prepare_queue_frame()
					self.queue_status.update_frame(grid_lol4)
					self.wallet_display_set.queue_frame_buttons( grid_lol4,self.queue_status)
					time.sleep(1)
					
					# here check amount didnt surpass confirmed - otherwise chanchge status to awaiting balance

					merged_queue_done=[]
					if rr[0]!='message':
						for jj,ss in enumerate(waiting):
							# print(jj,ss)
							if ss[3]!='send' or jj==ii or ss[0]=='message':
								continue 
							if ss[6]!='waiting':
								continue
							ddict2=json.loads(ss[4])
							if ddict2['fromaddr']!=ddict['fromaddr']:
								continue	
							
							#can be multiple items
							tmpsumadd=0
							for dd2 in ddict2['to']:							
								tmpsumadd+=float(dd2['a'])
								
							if sum_cur_spending+tmpsumadd>total_conf_per_addr-0.0001: # only pass that much which does not exceed total confirmed
								continue
								
							sum_cur_spending=sum_cur_spending+tmpsumadd #float(ddict2['to']['a'])
							
							merged_ii.append(jj)
							merged_queue_done.append(ss)
							ddict['to']=ddict['to']+ddict2['to']
					
					tostr=[]
					memo_orig=[]
					
					for to in ddict['to']:
						# validate amount, addr , memo cut 512
						table={}
						dt,ts=app_fun.now_to_str(False,ret_timestamp=True)
						if not self.the_wallet.validate_zaddr(to['z']):
							exceptions.append('Not valid destination address '+str(to['z'])+' - ignoring.')
							insert_notification('Not valid destination address '+str(to['z'])+' - ignoring.' ,{'fromaddr':ddict['fromaddr'],'to':[to]})
							 
							continue
						try:
							if float(to['a'])<0.0000001:
								exceptions.append('Too small amount '+str(to['a'])+' - ignoring.')
								
								insert_notification('Too small amount '+str(to['a'])+' - ignoring.' ,{'fromaddr':ddict['fromaddr'],'to':[to]})
								continue
						except:
							exceptions.append('Not valid amount '+str(to['a'])+' - ignoring.')
							
							insert_notification('Not valid amount '+str(to['a'])+' - ignoring.' ,{'fromaddr':ddict['fromaddr'],'to':[to]})
							continue
						
						tostr.append({"address":to['z'], "amount":float(to['a']), "memo":to['m'].encode('utf-8').hex() })
						
						memo_orig.append([to['m'],float(to['a']),to['z']]) 
					
					tmpres={}
					tmpres['opid']=''
					tmpres['result_details']='Bad amounts or not valid addresses.'
					tmpres["result"]='Failed - Nothing to process.'
					tmpres['exceptions']= '\n'.join(exceptions)	
					if len(tostr)>0:
						tostr=json.dumps(tostr)
						
						tmpres['opid']=str(self.the_wallet.send(ddict['fromaddr'],tostr))
						tmpres['opid']=tmpres['opid'].strip()
						
						cmdloc=['z_getoperationstatus','["'+tmpres['opid']+'"]']

						opstat=app_fun.run_process(self.cli_cmd,cmdloc)

						opj=''
						try:
							opj=json.loads(opstat)[0]
						except:
							opj={'error':{'message':opstat}}
						
						if 'error' in opj:
							tmpres['result_details']=str(opj['error']['message'].replace('shielded ','') )
							tmpres["result"]='Failed'
							
							insert_notification(tmpres['result_details'], {'fromaddr':ddict['fromaddr'],'to':[to]})
							
						else:
							ts=7
							while "result" not in opj:
								time.sleep(ts)
								if ts>1:
									ts=ts-1
								
								opstat=app_fun.run_process(self.cli_cmd,cmdloc)
								opj=json.loads(opstat)[0]
								
								if opj["status"]=="failed":
									tmpres["result"]='Failed'
									exceptions.append('Failed to process tx: '+opstat)
									insert_notification(opstat, {'fromaddr':ddict['fromaddr'],'to':[to]})
							
							if tmpres["result"]!='Failed':
								while opj["status"]=="executing":
									time.sleep(ts)
									if ts>1:
										ts=ts-1
									
									opstat=app_fun.run_process(self.cli_cmd,cmdloc)
									opj=json.loads(opstat)[0]
									print('while exe',opj)
									
								if opj["status"]=="success":
									tmpres["result"]='success'
									
								else:
									tmpres["result"]='Failed'
									exceptions.append('Failed to process tx: '+opstat)
									insert_notification(opstat, {'fromaddr':ddict['fromaddr'],'to':[to]})
									
								tmpres["result_details"]=str(opj["result"])
						
						del tmpres['opid'] # not needed later 
						
						tmpres["block"]=0 # get block nr for confirmation notarization validation later on 

						while tmpres["block"]==0:
							tmpinfo=self.the_wallet.getinfo()
							try:
								tmpinfo=int(tmpinfo["blocks"])
								if tmpinfo>0:
									tmpres["block"]=tmpinfo
									break
							except:
								print('Network problem')
								pass
							time.sleep(5)
							
							
							
						if tmpres["result"]=='success': # insert tx out:
							table={}
							txid=''
							if 'txid' in opj["result"]:
								txid=opj["result"]['txid']
								
							for mmii,mm in enumerate(memo_orig):
								mm0=mm[0].split('@zUnderNet')
								memo_orig[mmii][0]=mm0[0]
								
							dt,ts=app_fun.now_to_str(False,ret_timestamp=True)
							table['tx_history']=[{'Category':'send'
												, 'Type':'out'
												, 'status':'sent'
												,'txid':txid
												,'block':tmpres["block"] # estimated block sent for true nota conf estimation
												, 'timestamp':ts
												, 'date_time':dt
												,'from_str':ddict['fromaddr'] # for merge many from addr
												,'to_str':str(memo_orig)
												,'amount':sum_cur_spending
												, 'uid':'auto'
												 }]
							
							idb.insert(table,['Category','Type','status','txid','block','timestamp', 'date_time','from_str','to_str','amount','uid'])
							self.tx_history.update_history_frame()
							
							txid_utf8=txid 
							if rr[0]!='message':
								for mmii,mm in enumerate(memo_orig):
									
									table=self.the_wallet.prep_msgs_inout(txid_utf8,mm,'out',dt)
									if table['msgs_inout'][0]['msg']=='':
										table['msgs_inout'][0]['msg']='Sent amount '+str(round(sum_cur_spending,8))
									# if table=={}:
										# continue
																	 
									idb.insert(table,['proc_json','type','addr_ext','txid','tx_status','date_time', 'msg', 'uid','in_sign_uid'])
							else: #'message':
								mmm=['',0,memo_orig[0][2]]
								for mmii,mm in enumerate(memo_orig):
									mmm[0]+=mm[0]
									mmm[1]+=mm[1]
									
								table=self.the_wallet.prep_msgs_inout(txid_utf8,mmm,'out',dt)
								if table!={}:
									idb.insert(table,['proc_json','type','addr_ext','txid','tx_status','date_time', 'msg', 'uid','in_sign_uid'])
									
						self.messages.update_msgs()
						
						tmpres=json.dumps(tmpres)	
							
						table={}
						table['queue_done']=[{"type":rr[0],"wait_seconds":rr[1],"created_time":rr[2],"command":rr[3],"json":rr[4],"id":rr[5],"result":tmpres,'end_time':app_fun.now_to_str(False)}]
						idb.insert(table,["type","wait_seconds","created_time","command","json","id","result",'end_time'])

						for ss in merged_queue_done:
							table={}
							table['queue_done']=[{"type":ss[0],"wait_seconds":ss[1],"created_time":ss[2],"command":ss[3],"json":ss[4],"id":ss[5],"result":tmpres,'end_time':app_fun.now_to_str(False)}]
						
							idb.insert(table,["type","wait_seconds","created_time","command","json","id","result",'end_time'])
							
							table={}
							table['queue_waiting']=[{'status':'done'}]
							idb.update( table,['status'],{'id':[ '=',ss[5] ]})
					
					else:
						
						tmpres=json.dumps(tmpres)# some exceptions:
						table={}
						table['queue_done']=[{"type":rr[0],"wait_seconds":rr[1],"created_time":rr[2],"command":rr[3],"json":rr[4],"id":rr[5],"result":tmpres,'end_time':app_fun.now_to_str(False)}]
						idb.insert(table,["type","wait_seconds","created_time","command","json","id","result",'end_time'])
					
				else:
					tmpres="Wrong [from] address!"
					
					table={}
					table['queue_done']=[{"type":rr[0],"wait_seconds":rr[1],"created_time":rr[2],"command":rr[3],"json":rr[4],"id":rr[5],"result":tmpres,'end_time':app_fun.now_to_str(False)}]
						
					idb.insert(table,["type","wait_seconds","created_time","command","json","id","result",'end_time'])
					
			table={}
			table['queue_waiting']=[{'status':'done'}]
			idb.update( table,['status'],{'id':[ '=',rr[5] ], 'status':[ '=',"'processing'" ]})
			self.task_history.update_history_frame()
					
		idb.delete_where('queue_waiting',{'status':['<>',"'awaiting_balance'"],"command":['<>',"'send'"]  })
		grid_lol4=self.wallet_display_set.prepare_queue_frame()
		self.queue_status.update_frame(grid_lol4)
		self.wallet_display_set.queue_frame_buttons( grid_lol4,self.queue_status)
	
	
	def update_incoming_tx(self):
	
		if not hasattr(self.the_wallet, 'z_viewtransaction'):
			return
	
		try:
			y=json.loads(app_fun.run_process(self.cli_cmd,'getinfo'))
		
			notar=y["notarized"]
		except:
			return
			
		tmpwhere={'status':[' not in',"('reorged','notarized')"], 'Type':['=',"'in'"],'block':['<=',notar] }
		
		idb=localdb.DB()	
		toupdate=idb.select('tx_history', ["txid",'date_time'],tmpwhere) #
		
		if len(toupdate)>0: # check if update required ()
		
			for tt in toupdate:
		
				txidok=self.the_wallet.z_viewtransaction( tt[0] ) # if not in blocks anymore ? not valid ?
				tmpwhere2={'status':[' not in',"('reorged','notarized')"], 'Type':['=',"'in'"],'block':['<=',notar], 'txid':['=',"'"+tt[0]+"'"] }
				
				if txidok=='not valid txid' and datetime.datetime.now()>app_fun.datetime_from_str(tt[1])+datetime.timedelta(hours=1):
				
					table={}
					table['tx_history']=[{'status':'reorged'}]
					idb.update( table,['status'],tmpwhere2)
					
					table={}
					table['msgs_inout']=[{'tx_status':'reorged' }]
					idb.update( table,['tx_status' ], {'txid':['=', "'"+tt[0]+"'" ],'type':['=',"'received'"]})
					
				elif txidok!='not valid txid':
					table={}
					table['tx_history']=[{'status':'notarized'}]
					idb.update( table,['status'],tmpwhere2) # updating all, no matter outindex 
					
					table={}
					table['msgs_inout']=[{'tx_status':'notarized' }]
					idb.update( table,['tx_status'  ], {'txid':['=', "'"+tt[0]+"'" ],'type':['=',"'received'"]})
				# else wait
			self.tx_history.update_history_frame()
	
	
	
	
	def update_status(self):
				
		if self.started:
		
			# try:
			if True:
				gitmp=app_fun.run_process(self.cli_cmd,'getinfo')
				gi=json.loads(gitmp)
				tmpstr="Synced: "+str(gi["synced"])+"\nCurrent block: "+str(gi["blocks"])+"\nLongest chain: "+str(gi["longestchain"])+"\nNotarized: "+str(gi["notarized"])+"\nConnections: "+str(gi["connections"])
				
				if time.time()-self.insert_block_time>50: # check every 50 seconds
					self.insert_block_time=time.time()
					table={'block_time_logs':[{'uid':'auto', 'ttime':time.time(), 'block':gi["blocks"] }] }
					idbinit=localdb.DB('init.db')
					idbinit.upsert(table,['uid', 'ttime','block'],{'block':['=',gi["blocks"]]})
				
				self.output(tmpstr)
				
				if self.started:
					self.update_wallet()
					
				if self.started:
					self.update_incoming_tx()
					
				if self.started:
					self.process_queue()
						
		

	def set_wallet_widgets(self,statuselem,bstartstop,wallet_summary_frame,wallet_details,wds,queue_status,task_history,txhi,notif,messages):
		self.statustable=statuselem
		self.bstartstop=bstartstop
		self.wallet_summary_frame=wallet_summary_frame
		self.wallet_details=wallet_details #self.wallet_details.amount_per_address
		self.wallet_display_set=wds
		self.queue_status=queue_status
		self.task_history=task_history
		self.tx_history=txhi
		self.notifications=notif # self.notifications.update_notif_frame()
		self.messages=messages
		
		
		

	def __init__(self, deamon_cfg=None): 
		self.started=False
		self.insert_block_time=0
		self.the_wallet=None
		
		if deamon_cfg==None:
			return
			
		FULL_DEAMON_PARAMS=[ deamon_cfg['deamon-path'] , "-ac_name="+deamon_cfg["ac_name"]]
		CLI_STR=[deamon_cfg['cli-path'], "-ac_name="+deamon_cfg["ac_name"] ]
		ac_params_add_node=''
		
		if deamon_cfg["ac_params"].strip()!='':
			ac_params_add_node=deamon_cfg["ac_params"]
			
		if "addnode" in deamon_cfg:
			if len(deamon_cfg["addnode"])>0:
			
				for an in deamon_cfg["addnode"]:
					ac_params_add_node+=' -addnode='+an
			
		if len(ac_params_add_node.strip())>1:
			FULL_DEAMON_PARAMS+= ac_params_add_node.split(" ")  

		
		if deamon_cfg["datadir"].strip()!='': # adjust data dir
			FULL_DEAMON_PARAMS+=['-datadir='+deamon_cfg["datadir"] ] 
			CLI_STR+=['-datadir='+deamon_cfg["datadir"] ] 

		self.cli_cmd=CLI_STR
		self.deamon_par=FULL_DEAMON_PARAMS
		
	
	
	
	def stop_deamon(self):
	
		self.started=False
		self.output('Stopping deamon\n')
		self.run_subprocess(self.cli_cmd,'stop',2)
		


	def start_deamon(self, addrescan=False ):
	
		self.started=True
		
		tmpcond,tmppid=app_fun.check_deamon_running() # ''.join(self.deamon_par)
		
		if tmpcond:
		
			self.bstartstop.configure(state='normal')
			
			gitmp=app_fun.run_process(self.cli_cmd,'getinfo')
			while 'longestchain' not in gitmp:
				time.sleep(4)
				gitmp=app_fun.run_process(self.cli_cmd,'getinfo')
				self.output('Awaiting longest chain')
				
			if self.the_wallet==None: #hasattr(self,'the_wallet')==False or :
				self.the_wallet=wallet_api.Wallet(self.cli_cmd,self.get_last_load())
		
			y = json.loads(gitmp)
			if y["synced"]==True:
				self.bstartstop.configure(state='normal')
			else:
				self.bstartstop.configure(state='disabled')
				
			return 

		else:
			if self.decrypt_wallet()=='Cancell':
				return
				
			self.output('Starting deamon usually takes few minutes ...')
			reskanopt=[]
			if addrescan:
				reskanopt=['-rescan']
				
			self.run_subprocess([self.deamon_par+reskanopt,self.cli_cmd],'start',8)
			
			return
			
	
	def get_last_load(self):

		idb=localdb.DB( )
		last_load=-1
		if idb.check_table_exist( 'deamon_start_logs'):
			tt=idb.select_last_val( 'deamon_start_logs','loaded_block')

			if tt!=None:
				last_load=tt #[0][0]	
					
		return last_load
		
		
	def output(self,ostr): #self.output()
		if self.statustable==None: print(ostr)
		else:
			self.statustable.set(ostr)  
	
		
		
	def run_subprocess(self,CLI_STR,cmd_orig,sleep_s=2 ):

		if cmd_orig in ['start','stop']:
			
			self.bstartstop.configure(state='disabled')
	
		deamon_start=CLI_STR.copy()
		cli_cmd=CLI_STR.copy()
		cmd=cmd_orig
		deamon_warning="make sure server is running and you are connecting to the correct RPC port"
		
		t0=time.time()

		if cmd_orig=='start':
			deamon_start=CLI_STR[0]
			cli_cmd=CLI_STR[1]
			cmd=[]

		elif type(cmd_orig)!=type([]):
			
			cmdtmp=cmd_orig.split()
			cmd=[cmdii for cmdii in cmdtmp]
			
		tmplst=deamon_start +cmd 
		
		pp=subprocess.Popen( tmplst ) 
		
		time.sleep(sleep_s)
		
		tsyncing=None
		blocksinit=None
		
		while pp.poll()==None:
		
			if cmd_orig=='start':
			
				gitmp=app_fun.run_process(cli_cmd,'getinfo')
				
				if deamon_warning in gitmp:
					self.output(gitmp)
				elif 'error message:' in gitmp:
					tmps=gitmp.split('error message:')
					self.output(tmps[1].strip()+'\n')
					
				elif 'is not recognized' in gitmp or 'exe' in gitmp:
					self.output('Command ['+cli_cmd+" getinfo"+'] not recognized - wrong path ? Exiting.')
					exit()
				elif 'longestchain' in gitmp:
				
					y = json.loads(gitmp)
					gtmpstr="Synced: "+str(y["synced"])+"\nCurrent block: "+str(y["blocks"])+"\nLongest chain: "+str(y["longestchain"])+"\nConnections: "+str(y["connections"])
				
					if y['longestchain']==y["blocks"] and y['longestchain']>0:
						if cmd_orig=='start':
							self.output('Wallet synced!')
							
						break
					elif y['longestchain']>0:
						
						timeleft=''
						if tsyncing==None and y["blocks"]>0 and y["longestchain"]-y["blocks"]>0:
						
							tsyncing=time.time()
							blocksinit=y["blocks"]
							
						elif y["blocks"]>0 and y["longestchain"]-y["blocks"]>0:
							secpassed=time.time()-tsyncing
							blockssynced=y["blocks"]-blocksinit
							syncspeed=blockssynced/secpassed
							blocksleft=y["longestchain"]-y["blocks"]
							timeleft=int(blocksleft/syncspeed)
							hoursleft=0
							minutesleft=0
							secondsleft=int(timeleft)
							if timeleft>3600:
								hoursleft=int(timeleft/3600)
								secondsleft=int(timeleft-hoursleft*3600)
							if secondsleft>60:
								minutesleft=int(secondsleft/60)
								secondsleft=int(secondsleft-minutesleft*60)
									
							timeleft='Estimated time left: '+str(hoursleft)+' h '+str(minutesleft)+' m '+str(secondsleft)+' s'
							
							if hoursleft>1:
								timeleft+='\nConsider downloading bootstrap for faster sync.'
							
						tmpstr='Syncing ... \nLoaded blocks: '+str(y["blocks"])+' of '+str(y["longestchain"])+' ('+str(int(100*y["blocks"]/y["longestchain"]))+'%)' +'\nBlocks to catch up: '+str(y["longestchain"]-y["blocks"])+'\n'+timeleft+'\n'
						
						
						self.output(tmpstr)
						
					else:
						self.output(gtmpstr)
						
				else:
					self.output(gitmp)
					
			if sleep_s>4:
				sleep_s=int(sleep_s-2)
				
			if sleep_s<4: # can be for 3 reason, hence separate
				sleep_s=4
					
			if self.statustable==None: printsleep(sleep_s)
			else: 
				for ti in range(int(sleep_s)):
					tmptmptmp=self.statustable.get()
					
					self.statustable.set(self.statustable.get()+' .') #.set_textvariable(None,self.statustable.get()+' .')
					time.sleep(1)
		 
		
		if cmd_orig=='start':		
			self.the_wallet=wallet_api.Wallet(self.cli_cmd,self.get_last_load())
			
			tend=time.time()
			tdiff=int(tend-t0)
			y = json.loads(gitmp)
			
			loaded_block=y["blocks"]
			
			# save loading time
			idb=localdb.DB()
			table={}
			
			table['deamon_start_logs']=[{'uid':'auto', 'time_sec':tdiff, 'ttime':tend, 'loaded_block':loaded_block }]
			idb.insert(table,['uid','time_sec','ttime','loaded_block'])
			
			self.bstartstop.configure(state='normal')
			
		elif cmd_orig=='stop':
		
			self.started=False
			
			tmpcond,tmppid=app_fun.check_deamon_running() # additiona lcheck needed for full stop
			while tmpcond:
				self.statustable.set(self.statustable.get()+'.') #.set_textvariable(None,self.statustable.get()+' .')
				time.sleep(2)
				tmpcond,tmppid=app_fun.check_deamon_running()
			
			self.the_wallet=None
			
			self.bstartstop.configure(state='normal')
			self.output('Blockchain stopped')
			
			self.encrypt_wallet_and_data()
		
	def decrypt_wallet(self):
		
		idb=localdb.DB('init.db')
		ppath=idb.select('init_settings',['datadir'] )
		
		if self.wallet_display_set.password==None:
			if not os.path.exists(os.path.join(ppath[0][0],'wallet.dat') ):
				addstr=''
				if os.path.exists(os.path.join(ppath[0][0],'wallet.encr') ):
					addstr=' However wallet.encr EXISTS - MAYBE YOU SHOULD RUN WITH PASSWORD OPTION? '
				
				if flexitable.msg_yes_no("Wallet file missing!", 'There is no wallet.dat file in the directory \n\n'+ppath[0][0]+'\n'+addstr+'\n\n ARE YOU SURE YOU WANT TO PROCEEED?? A NEW WALLET WILL BE CREATED!'):
								
					return 'New wallet accepted'
				else:
					return 'Cancell'
			else:
				return 'wallet.dat exists'
			
		
		
		if os.path.exists(os.path.join(ppath[0][0],'wallet.dat') ):
			print('Already decrypted')
		
		elif os.path.exists(os.path.join(ppath[0][0],'wallet.encr') ):
			cc=aes.Crypto()
			cc.aes_decrypt_file( ppath[0][0]+'/wallet.encr', ppath[0][0]+'/wallet.dat' , self.wallet_display_set.password)
			# os.remove(ppath[0][0]+'/wallet.encr')
			app_fun.secure_delete(ppath[0][0]+'/wallet.encr')
		else:
			 flexitable.messagebox_showinfo('Wallet file missing!', 'There is no wallet.encr file in the directory \n\n'+ppath[0][0]+'\n\n Will create new wallet file!')
			 # return 'Cancell'
		
		return 'Decrypted'
			
	def encrypt_wallet_and_data(self):
		
		if self.wallet_display_set.password==None:
			return
			
		idb=localdb.DB('init.db')
		ppath=idb.select('init_settings',['datadir'] )
		
		cc=aes.Crypto()
		cc.aes_encrypt_file( ppath[0][0]+'/wallet.dat', ppath[0][0]+'/wallet.encr' , self.wallet_display_set.password)
		app_fun.secure_delete(ppath[0][0]+'/wallet.dat')
		
	
