import sys, os, glob, mimetypes, time, html, json, io
from configparser import ConfigParser
from zipfile import ZipFile
from bs4 import BeautifulSoup
from oauth2client import client
from googleapiclient import sample_tools
from apiclient.http import MediaFileUpload
from imgurpython import ImgurClient

# set default config and read config.cfg if it exists
config = ConfigParser()
config['DEFAULT'] = {'blogger_blog_id':'0', 'imgur_client_id':'8d3b82bde368ee1', 'tumblr_archive_path':'./archive.zip', 'draft':True}
if os.path.exists('config.cfg'):
	config.read('config.cfg')

blog_id = config.get('default', 'blogger_blog_id')
imgur_client_id = config.get('default', 'imgur_client_id')
draft = config.getboolean('default', 'draft')
backup_path = os.path.abspath(config.get('default', 'tumblr_archive_path'))


imgur = ImgurClient(imgur_client_id, '')

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
				with open('posts.xml', 'rb') as posts_f:
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
					post_date = post.get('date')
					print('Loading Tumblr post ID: '+post_id+', type: '+post.get('type'))
					if post.get('type') == 'photo':
						photo_url = post.find('photo-url')
						if photo_url:
							# get caption
							caption = post.find('photo-caption')
							# get tags
							tag_list = []
							tags = post.find_all('tag')
							for tag in tags:
								if tag.text:
									tag_list.append(tag.text)
							# get photos
							files = []
							if not backup_is_archive:
								files = glob.glob(os.path.join(os.path.join(backup_path, 'media'), post_id+'*.jpg'))
								files.extend(glob.glob(os.path.join(os.path.join(backup_path, 'media'), post_id+'*.png')))
							else:
								for file in files_all:
									if file.startswith('/media/'+post_id):
										files.append(file)
							files = sorted(files, key=lambda item: (int(item.partition(' ')[0]) if item[0].isdigit() else float('inf'), item))
							images = []
							# upload to imgur
							for filename in files:
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
							src = '<div class="photoset">'
							for image in images:
								src = '<a href="'+image+'"><img src="'+image+'"/></a>'
							src += '<div class="description">'+html.unescape(caption.text)+'</div></div>'
							body = {
								"kind": "blogger#post",
								"id": blog_id,
								"title": post_date,
								"content":src,
								"labels":tag_list,
							}
							new_post = blog_posts.insert(blogId=blog['id'], body=body, isDraft=draft).execute()
							blog_info['posted_ids'].append(post_id)
							print('  Blogger upload', new_post.get('url'))
							time.sleep(0.1)
					print(' ')
	except client.AccessTokenRefreshError:
		print('The credentials have been revoked or expired, please re-run the application to re-authorize')
	except KeyboardInterrupt:
		print('Exiting (KeyboardInterrupt)')
	except Exception as e:
		print(e)
	if main_archive:
		main_archive.close()
	if len(blog_info['posted_ids']) > 0:
		with open('blog_info.json', 'wb') as f:
			print('Saving blog info...')
			f.write(bytes(json.dumps(blog_info),'utf-8'))
	print('Done.')
if __name__ == '__main__':
	main(sys.argv)