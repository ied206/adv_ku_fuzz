try:
	import sys
	import codecs
	import inspect

except:
	print('Library Error')
	sys.exit(0)


def main():
	try:
		input_code = openSourceCode(sys.argv[2])
	except:
		print('File is not exist')
	

if __name__ == '__main__':
	if len(sys.argv) != 3:
		print('usage : python fuzzer.py <option> <filename>')
		sys.exit(0)
	else:
		main()