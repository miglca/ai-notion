import logging

from quart import Quart, render_template, flash, request, jsonify
from werkzeug.utils import secure_filename

import secrets

from NotionAI.NotionAI import *
from utils.utils import ask_server_port, save_options, save_data, createFolder

UPLOAD_FOLDER = '../app/uploads/'
ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'webp'])

app = Quart(__name__)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
logging.basicConfig(filename='app.log', filemode='w', format='%(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

notion = None


@app.route('/add_url_to_mind')
async def add_url_to_mind():
    url = request.args.get('url')
    title = request.args.get('title')
    collection_index = request.args.get('collection_index')
    notion.set_mind_extension(request.user_agent.platform)
    return str(notion.add_url_to_database(url, title,int(collection_index)))


@app.route('/add_text_to_mind')
async def add_text_to_mind():
    url = request.args.get('url')
    text = request.args.get('text')
    collection_index = request.args.get('collection_index')
    notion.set_mind_extension(request.user_agent.platform)

    if len(request.args) > 4:
        l = request.args.to_dict()
        addition_list = list(l)[3:]
        addition = '&'.join(str(text) for text in addition_list)
        text = text + "&" + addition

    return str(notion.add_text_to_database(text, url,int(collection_index)))


@app.route('/add_image_to_mind')
async def add_image_to_mind():
    url = request.args.get('url')
    image_src = request.args.get('image_src')
    image_src_url = request.args.get('image_src_url')
    collection_index = request.args.get('collection_index')

    notion.set_mind_extension(request.user_agent.platform)
    return str(notion.add_image_to_database(image_src, url, image_src_url,int(collection_index)))


@app.route('/get_mind_structure')
async def get_mind_structure():
    return jsonify(structure=notion.mind_structure.get_mind_structure())


@app.route('/modify_element_by_id')
async def modify_element_by_id():
    id = request.args.get('id')
    title = request.args.get('new_title')
    url = request.args.get('new_url')
    notion.set_mind_extension(request.user_agent.platform)
    return str(notion.modify_row_by_id(id, title, url))


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/upload_file', methods=['POST'])
async def upload_file():
    createFolder("uploads")
    status_code = 200
    # check if the post request has the file part
    request_files = await request.files

    if 'file' not in request_files:
        flash('No file part')
        status_code = 500

    file = request_files['file']
    # if user does not select file, browser also
    # submit an empty part without filename
    if file.filename == '':
        flash('No selected file')
        status_code = 500
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        uri = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        return str(notion.add_image_to_database(uri))
    else:
        print("This file is not allowed to be post")
        status_code = 500
    return str(notion.create_json_response(status_code=status_code))


@app.route('/get_current_mind_url')
async def get_current_mind_url():
    return str(notion.data['url'])


@app.route('/update_notion_tokenv2')
async def update_notion_tokenv2():
    token_from_extension = request.args.get('tokenv2')
    changed = False
    with open('data.json') as json_file:
        options = json.load(json_file)

        if token_from_extension != options['token']:
            try:
                options['token'] = token_from_extension

                client = NotionClient(token_v2=options['token'])  # if can't make a client out of the token, it is not
                # a correct one.

                a_file = open("data.json", "w")
                json.dump(options, a_file)
                a_file.close()

                logging.info("Token v2 changed to {}".format(token_from_extension))
                changed = notion.run()
            except requests.exceptions.HTTPError:
                logging.info("Incorrect token V2 from notion")
    return str(changed)


@app.route('/')
async def show_settings_home_menu():
    return await render_template("options.html")


@app.route('/handle_data', methods=['POST'])
async def handle_data():
    data = await request.get_json()
    print(data)
    notion_url = data['notion_url']

    notion_token = data['notion_token']

    use_email = data['email'] and data['password']

    if data['clarifai_key']:
        clarifai_key = data['clarifai_key']
        save_data(logging, url=notion_url, token=notion_token, clarifai_key=clarifai_key)
        use_clarifai = True
    else:
        save_data(logging, url=notion_url, token=notion_token)
        use_clarifai = False

    if "delete_after_tagging" in data:
        delete_after_tagging = data['delete_after_tagging']
    else:
        delete_after_tagging = False

    save_options(logging, use_clarifai=use_clarifai, delete_after_tagging=delete_after_tagging)

    if use_email:
        has_run = notion.run(logging, email=data['email'], password=data['password'])
    else:
        has_run = notion.run(logging)

    if has_run:
        return "200"
    else:
        return "500"


if __name__ == "__main__":
    secret = secrets.token_urlsafe(32)
    app.secret_key = secret
    port = ask_server_port(logging)
    notion = NotionAI(logging, port)
    app.run(host="0.0.0.0", port=port, debug=True)
