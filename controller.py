import cmd
import psutil
import sys
import subprocess

pnames = ['monitor', 'responder', 'messenger']

class Controller(cmd.Cmd):
	intro = 'GotEiim2 Bot Interactive Shell'
	prompt = '🤖 '
	
	def do_status(self, line):
		for process in psutil.process_iter():
			if(process.status() != 'stopped' and "python" in process.name()):
				for name in pnames:
					if(f'{name}.py' in process.cmdline()):
						print(f'{name.capitalize()} running')
	
	def do_kill(self, name):
		if(name == "all"):
			[do_kill(self, n) for n in pnames]
		if(not name in pnames):
			print("Need a process to kill")
			return
		for process in psutil.process_iter():
			if(process.status() != 'stopped' and "python" in process.name() and name+".py" in process.cmdline()):
				process.kill()
				print("Killed")
	
	def do_start(self, name):
		if(name == "all"):
			[do_start(self, n) for n in pnames]
		if(not name in pnames):
			print("Need a process to start")
			return
		outfile = open(name+'.out', 'a')
		subprocess.Popen([sys.executable, name+".py"], stdout=outfile, stdin=outfile)
		print("Started")
		
	def do_restart(self, name):
		self.do_kill(name)
		self.do_start(name)
		
	def do_exit(self, line):
		return True
	
if __name__ == '__main__':
	Controller().cmdloop()