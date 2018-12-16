import sys, os, glob, time, html, json, io
from configparser import ConfigParser
from zipfile import ZipFile
from bs4 import BeautifulSoup
from oauth2client import client
from googleapiclient import sample_tools
from imgurpython import ImgurClient

# optional ipfs
try:
	import ipfsapi
except:
	pass

# set default config and read config.cfg if it exists
config = ConfigParser()
config['default'] = {'blogger_blog_id':'0', 'imgur_client_id':'0', 'tumblr_archive_path':'./archive.zip', 'draft':True, 'use_ipfs':False}
if os.path.exists('config.cfg'):
	config.read('config.cfg')

blog_id = config.get('default', 'blogger_blog_id')
imgur_client_id = config.get('default', 'imgur_client_id')
draft = config.getboolean('default', 'draft')
use_ipfs = config.getboolean('default', 'use_ipfs') and 'ipfsapi' in dir() # will post to a local ipfs daemon instead of imgur

backup_path = os.path.abspath(config.get('default', 'tumblr_archive_path'))

ipfs = None
if not use_ipfs:
	imgur = ImgurClient(imgur_client_id, '')
else:
	ipfs = ipfsapi.connect('127.0.0.1', 5001)

blog_info = {'posted_ids':[]} # contains the tumblr post ID's that have been posted to blogger
if os.path.exists('blog_info.json'):
	with open('blog_info.json', 'rb') as f:
		try:
			blog_info = json.loads(f.read())
		except:
			pass
def is_path_archive():
	if os.path.isfile(backup_path) and backup_path.endswith('.zip'):
		with ZipFile(backup_path, 'r') as archive:
			return True
	return False

def main(argv):
	global blog_info
	backup_is_archive = is_path_archive()
	posts_xml = None
	files_all = []
	main_archive = None
	# get archive info
	if not backup_is_archive:
		posts_zip = os.path.join(backup_path, 'posts.zip')
		if not os.path.exists(posts_zip):
			print('Can\'t find Tumblr archive file or extracted posts.zip')
			sys.exit()
		with ZipFile(posts_zip, 'r') as archive:
			with archive.open('/posts.xml') as posts_f:
				posts_xml = posts_f.read()
	else:
		main_archive = ZipFile(backup_path, 'r')
		with main_archive.open('/posts.zip', 'r') as posts_zip:
			with ZipFile(io.BytesIO(posts_zip.read()), 'r') as archive:
				with archive.open('/posts.xml') as posts_f:
					posts_xml = posts_f.read()
		files_all = main_archive.namelist()
	if backup_is_archive:
		print('Loading from archive')
	else:
		print('Loading from folder')

	# blogger stuff
	service, flags = sample_tools.init(
		argv, 'blogger', 'v3', __doc__, __file__,
		scope='https://www.googleapis.com/auth/blogger')

	try:
		users = service.users()
		this_user = users.get(userId='self').execute()

		blogs = service.blogs()

		# Retrieve the list of Blogs this user has write privileges on
		writeable_blogs = blogs.listByUser(userId='self').execute()

		blog_posts = service.posts()
		for blog in writeable_blogs['items']:
			if blog['id'] == blog_id:
				soup = BeautifulSoup(posts_xml, 'lxml')
				posts = soup.find_all('post')
				posts.reverse()
				for post in posts:
					post_id = post.get('id')
					if post_id in blog_info['posted_ids']:
						continue
					post_date = post.get('date')
					title = post_date
					if post.get('is_reblog','false') == 'true':
						continue
					print('Loading Tumblr post ID: '+post_id+', type: '+post.get('type'))
					# get tags
					tag_list = []
					tags = post.find_all('tag')
					for tag in tags:
						if tag.text:
							tag_list.append(tag.text)
					body = '<div class="original-date">Originally posted: '+post_date+'</div><br/>'
					if post.get('type') == 'video':
						print('  Skipping video post...')
						continue
					if post.get('type') == 'regular':
						regular_body = post.find('regular-body')
						regular_title = post.find('regular-title')
						if regular_body:
							body += regular_body.text
						if regular_title:
							title = regular_title.text
					if post.get('type') == 'answer':
						answer = post.find('answer')
						question = post.find('question')
						if question:
							body += '<blockquote class="question">'+question.text+'<blockquote>'
						if answer:
							body += '<blockquote class="answer">'+answer.text+'<blockquote>'
					if post.get('type') == 'quote':
						quote_text = post.find('quote-text')
						quote_source = post.find('quote-source')
						if quote_text:
							body += '<blockquote class="quote-text">'+quote_text.text+'<blockquote>'
							if quote_source:
								body += '<div class="quote-source">'+quote_text.text+'<div><br/>'
					if post.get('type') == 'conversation':
						conversation_title = post.get('conversation-title')
						conversation_text = post.get('conversation-text')
						if conversation_title:
							title = conversation_title.text
						if conversation_text:
							body += '<blockquote class="conversation-text">'+conversation_text+'</blockquote><br/>'
						# todo: add conversation/line tags
					if post.get('type') == 'photo':
						pass
					photo_url = post.find('photo-url')
					captions = []
					if photo_url:
						# get caption
						captions = post.find_all('photo-caption') or []
					# get photos
					files = []
					if not backup_is_archive:
						files = glob.glob(os.path.join(os.path.join(backup_path, 'media'), post_id+'*.jpg'))
						files.extend(glob.glob(os.path.join(os.path.join(backup_path, 'media'), post_id+'*.png')))
						files.extend(glob.glob(os.path.join(os.path.join(backup_path, 'media'), post_id+'*.gif')))
					else:
						for file in files_all:
							if file.startswith('/media/'+post_id):
								files.append(file)
					files = sorted(files, key=lambda item: (int(item.partition(' ')[0]) if item[0].isdigit() else float('inf'), item))
					images = []
					# upload to imgur
					for filename in files:
						if not use_ipfs:
							image = {}
							if not backup_is_archive:
								image = imgur.upload_from_path(filename, config=None, anon=True)
							else:
								with main_archive.open(filename, 'r') as f, open('./temp', 'wb') as f2:
									f2.write(f.read())
									image = imgur.upload_from_path('./temp', config=None, anon=True)
								os.remove('./temp')
							if image.get('link'):
								images.append(image.get('link'))
							if image.get('deletehash'):
								print('  Imgur upload', image.get('link'), ' deletehash: ', image.get('deletehash'))
							time.sleep(0.2)
						else:
							image_hash = None
							if not backup_is_archive:
								image_hash = ipfs.add(filename).get('Hash')
							else:
								with main_archive.open(filename, 'r') as f:
									image_hash = ipfs.add_bytes(f.read())
							if image_hash:
								with open('ipfs_pin_'+blog_id+'.sh', 'a') as f:
									f.write('ipfs pin add '+image_hash+'\r\n')
								images.append('https://ipfs.io/ipfs/'+image_hash)
								print('  ipfs upload', 'https://ipfs.io/ipfs/'+image_hash)
					if post.get('type') == 'photo':
						body += '<div class="photoset">'
					for image in images:
						body += '<div class="photo"><a href="'+image+'"><img src="'+image+'"/></a></div><br/>'
					for caption in captions:
						body += '<div class="photo-caption">'+html.unescape(caption.text)+'</div><br/>'
					if post.get('type') == 'photo':
						body += '</div>'
					body_json = {
						"kind": "blogger#post",
						"id": blog_id,
						"title": title,
						"content":body,
						"labels":tag_list,
					}
					new_post = blog_posts.insert(blogId=blog['id'], body=body_json, isDraft=draft).execute()
					blog_info['posted_ids'].append(post_id)
					print('  Blogger upload', new_post.get('url'), '"'+title+'"')
					print(' ')
					time.sleep(0.25)
	except client.AccessTokenRefreshError:
		print('The credentials have been revoked or expired, please re-run the application to re-authorize')
	except KeyboardInterrupt:
		print('Exiting (KeyboardInterrupt)')
	if main_archive:
		main_archive.close()
	if len(blog_info['posted_ids']) > 0:
		with open('blog_info.json', 'wb') as f:
			print('Saving blog info...')
			f.write(bytes(json.dumps(blog_info),'utf-8'))
	print('Done.')
if __name__ == '__main__':
	main(sys.argv)
