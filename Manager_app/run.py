from multiprocessing import Process

def manager_control(): # manager_check & start elb
    import manager

def web_applicaton(): # manager_web app
    import webapp_run

if __name__ == '__main__':
    Process(target = manager_control).start()
    Process(target = web_applicaton).start()
