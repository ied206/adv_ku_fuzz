try:
	import sys
	import codecs
	import inspect
	import os
#os.urandom(n)
#os.urandom(os.urandom(4))

except:
	print('Library Error')
	sys.exit(0)

crash_data=list()

def openSourceCode(fileName):

	# open Source Code
	try:

		with codecs.open(fileName, 'r', encoding = 'UTF-8') as f:

			code = f.read()

		return code

	except:

		print('Can not open source file')
		sys.exit(0)

def byte_array_to_int(arr):
	sum=0
	for i in range(len(arr)):
		sum=sum+ord(arr[i])*pow(16,len(arr)-i-1)
	return sum

def int_fuzzer(iter,file_name):
	for i in range(0,iter) :
		result=1
		if(i%10000 == 0):
			print("iter: "+str(i))
		fuzz_data = os.urandom(4)
		fuzz_data = byte_array_to_int(fuzz_data)
		result=os.system('(echo {} | ./{} )'.format(fuzz_data,file_name))
		print("result: " + str(result))
		if(result != 0 ):
			crash_data.append(result)

def string_fuzzer(iter,file_name):
	for i in range(0,iter):
		fuzz_data = os.urandom(os.urandom(4))
		result = os.system('(echo {} | ./{} )'.format(fuzz_data, file_name))
		print("result: " + str(result))
		if(result !=0):
			crash_data.append(result)

def mutate_chunk(byte_stream):
	chunk_size = len(byte_stream)
	changed_chunk = list()
	for i in range(chunk_size):
		option = ord(os.urandom(1)) % 4
		changed_chunk.append(byte_stream[i])
		if(option == 0):
			changed_chunk.append(os.urandom(1))
		elif(option == 1):
			changed_chunk.pop(len(changed_chunk)-1)
		elif(option == 2):
			changed_chunk.pop(len(changed_chunk) - 1)
			changed_chunk.append(byte_stream[os.urandom(1)%len(byte_stream)])
		else:
			if(i+2 < len(byte_stream)):
				temp =byte_stream[i+1]
				byte_stream[i+1]=byte_stream[i+2]
				byte_stream[i+2]=temp
				changed_chunk.append(byte_stream[i+1])
				i=i+1


def main():
	if (sys.argv[1] == "int"):
		int_fuzzer(100,sys.argv[2])
	elif (sys.argv[1] == "string"):
		string_fuzzer(100, sys.argv[2])
	#elif (sys.argv[1] == "byte"):
		#TODO
	else:
		print("Option error! ")
		sys.exit(0)
	print(len(crash_data))

if __name__ == '__main__':
	if len(sys.argv) != 3:
		print('usage : python fuzzer.py <option> <filename>')
		sys.exit(0)
	else:
		main()