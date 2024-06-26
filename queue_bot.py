import time
import os
import argparse 

from core.queue_checker import QueueChecker

every_hours = 1.1
queue_checker = QueueChecker('new_delhi', '10771', '284efad7')

success = False
while not success:
	if not os.path.isfile(queue_checker.order_id+"_"+queue_checker.code+"_success.txt"):
		queue_checker.check_queue()
		time.sleep(every_hours*3600)
	else:
		print('file exists, exiting')
		success = True



# if __name__ == '__main__':
# 		
#  	parser = argparse.ArgumentParser(description='Parameters for checking')

#  	parser.add_argument('--subdomain',
# 	                       type=str, required=True,
# 	                       help='The city where the consulate is situated')
 	
#  	parser.add_argument('--order_id',
# 	                       type=str, required=True,
# 	                       help='Номер заявки')
 	
#  	parser.add_argument('--code',
# 	                       type=str, required=True, 
# 	                       help='Защитный код')
 	
#  	parser.add_argument('--every_hours',
# 	                       type=int, default=3,
# 	                       help='Every n hours to check the queue, default 2')
 	
#  	args = parser.parse_args()
# 	
#  	queue_checker = QueueChecker(args.subdomain, args.order_id, args.code)
# 	
#  	run(queue_checker, args.every_hours)
