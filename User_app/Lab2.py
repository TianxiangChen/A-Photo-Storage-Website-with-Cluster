from app import *
from User import User
import os
from flask import render_template, session, request, flash, redirect, url_for, send_from_directory, send_file
from app.forms.Forms import SignupForm, SigninForm, EasyUploadForm
from Photo import Photo
from wand.image import Image
import random
import string
import boto3

SUPPORTED_EXT = ['.jpg', '.jpeg', '.png']
RANDOM_LENGTH = 8

@webapp.route('/')
def home():
    return redirect(url_for('profile'))

# handle error
@webapp.errorhandler(404)
def page_not_found(e):
    return render_template('error.html'), 404

"""URI support for test function."""
@webapp.route('/test/EasyUpload', methods=['GET', 'POST'])
def easy_upload():
    form = EasyUploadForm()

    if request.method == 'GET':
        if 'username' in session:
            # if user is logged in
            return redirect(url_for('profile'))
        return render_template('easy_upload.html', form=form)

    elif request.method == 'POST':
        if not form.validate():
            return render_template('easy_upload.html', form=form)
        else:
            # usr is authenticated

            session['username'] = form.userID.data
            user = User.query.filter_by(username=session['username']).first()
            if not user:
                return 'user:db'

            session['username'] = form.userID.data
            request_files = request.files.getlist("uploadedfile")
            save_photos(request_files, user)



            return render_template('easy_upload.html', form=form, success=True)


@webapp.route('/test/FileUpload', methods=['GET', 'POST'])
def test_file_upload():
    if request.method == 'GET':
        return render_template('testFileUpload.html')
    else:
        # POSTING
        userID = request.form['userID']
        passwd = request.form['password']
        files = request.files.getlist('uploadedfile')
        user = User.query.filter_by(username=userID).first()
        if not user:
            return render_template('testFileUpload.html', error="User doesn't exist")
        if not user.check_password(passwd):
            return render_template('testFileUpload.html', error="Wrong password")

        # user authenticated
        save_photos(files, user)
        return render_template('testFileUpload.html')

"""Signin page handler."""
@webapp.route('/signin', methods=['GET', 'POST'])
def signin():
    form = SigninForm()

    if request.method == 'GET':
        if 'username' in session:
            # if user is logged in
            return redirect(url_for('profile'))
        return render_template('signin.html', form=form)
    elif request.method == 'POST':
        if not form.validate():
            return render_template('signin.html', form=form)
        else:
            # usr authenticated
            session['username'] = form.username.data
            user = User.query.filter_by(username=session['username']).first()
            if not user:
                return 'user:db'

            session['username'] = form.username.data
            return redirect(url_for('profile'))


"""Process user signout, return to signin page."""
@webapp.route('/signout')
def signout():
    if 'username' not in session:
        return redirect(url_for('signin'))

    session.pop('username', None)
    return redirect(url_for('signin'))


"""Signup page, handles DB calls too."""
@webapp.route('/signup', methods=['GET', 'POST'])
def signup():
    form = SignupForm()

    if request.method == 'GET':
        if 'username' in session:
            # if user is logged in
            return redirect(url_for('profile'))

        return render_template('signup.html', form=form)

    elif request.method == 'POST':
        if form.validate():
            # validation succ
            new_user = User(form.username.data, form.email.data, form.password.data)
            db.session.add(new_user)
            db.session.commit()

            # save cookie
            session['username'] = new_user.username
            return redirect(url_for('profile'))
        else:
            # validation failed
            return render_template('signup.html', form=form)


"""Method called when uploading image, process images and stored to DB."""
@webapp.route('/upload', methods=['POST'])
def upload():
    if not 'username' in session:
        return redirect(url_for('signin'))

    user = User.query.filter_by(username = session['username']).first()
    if not user:
        return 'user:db'

    request_files = request.files.getlist("file")
    print(request_files)
    if request_files[0].filename == '':
        return render_template('upload.html', error='No file selected')

    save_photos(request_files, user)

    return redirect(url_for('profile'))


"""Helper used to send images to clients."""
@webapp.route('/upload/<path>/<filename>')
def send_image(path, filename):
    return send_from_directory(os.path.join(IMAGE_STORE, path), filename)


"""Handles request for profile, packs all related images and send to user."""
@webapp.route('/profile')
def profile():
    if not user_logged_in():
        return redirect(url_for('signin'))

    # locate the user
    user = User.query.filter_by(username = session['username']).first()
    if not user:
        return 'user:db'

    #locate images by user
    images = Photo.query.filter_by(uid = user.uid).all()

    image_names = [photo.origin_pic_path for photo in images]
    image_and_transforms = {}
    for photo in images:
        image_and_transforms[S3_ADDR + photo.thumbnail_path] = [S3_ADDR + photo.origin_pic_path,
                                                                S3_ADDR + photo.t1_pic_path,
                                                                S3_ADDR + photo.t2_pic_path,
                                                                S3_ADDR + photo.t3_pic_path]


    print(image_names)

    return render_template("profile.html", image_dict=image_and_transforms)


"""Displays form used to upload images"""
@webapp.route('/upload_form', methods=['get'])
def upload_form():
    if not user_logged_in():
        return redirect(url_for('signin'))

    return render_template('upload.html', error=None)

@webapp.route('/about')
def about():
    return render_template('about.html')


def user_logged_in():
    return 'username' in session


"""Reads the list of uploaded files, process them and store to DB
under the given user"""
def save_photos(file_list, user):
   for upload_file in file_list:
        filename = upload_file.filename
        print('Filename: %s' % filename)

        # check file ext
        ext = os.path.splitext(filename)[1]
        if ext.lower() in SUPPORTED_EXT:
            print("File supported moving on...")
        else:
            return render_template('upload.html', error='Extension not supported')

        # make user folder
        user_image_folder = TMP_FOLDER
        if not os.path.exists(user_image_folder):
            os.makedirs(user_image_folder)

        # store image
        # randomize filename, used as a 'basefile'
        random_string = ''.join(random.choice(string.ascii_uppercase + string.digits)
                                for _ in range(RANDOM_LENGTH))
        filename = random_string + ext

        destination = os.path.join(user_image_folder, filename)
        print("Save upload to:", destination)
        upload_file.save(destination)
        original_filename = random_string + ext
        save_file(destination, filename)
        # transform images
        with Image(filename=destination) as img:
            with img.clone() as resize:
                resize.transform(resize='640x480>')
                thumbnail_filename = random_string + '_thumb.jpg'
                destination = filename=os.path.join(user_image_folder, thumbnail_filename)
                resize.save(filename=destination)
                save_file(destination, thumbnail_filename)

            with img.clone() as rotate:
                rotate.flip()
                t1_filename = random_string + '_t1.jpg'
                destination = filename=os.path.join(user_image_folder, t1_filename)
                rotate.save(filename=destination)
                save_file(destination, t1_filename)

            with img.clone() as shift:
                shift.evaluate(operator='rightshift', value=1, channel='blue')
                t2_filename = random_string + '_t2.jpg'
                destination = filename=os.path.join(user_image_folder, t2_filename)
                shift.save(filename=destination)
                save_file(destination, t2_filename)

            with img.clone() as level:
                level.level(0.2, 0.9, gamma=1.1)
                t3_filename = random_string + '_t3.jpg'
                destination = filename=os.path.join(user_image_folder, t3_filename)
                level.save(filename=destination)
                save_file(destination, t3_filename)

        clear_tmp_folder()

        # handle database
        new_photo = Photo(user.uid, original_filename, thumbnail_filename,
                          t1_filename, t2_filename, t3_filename)
        db.session.add(new_photo)
        db.session.commit()



def clear_tmp_folder():
    folder = TMP_FOLDER
    for the_file in os.listdir(folder):
        file_path = os.path.join(folder, the_file)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
        except Exception as e:
            print(e)


def save_file(file_to_save, filename):
    s3 = boto3.resource('s3')
    s3.Bucket(IMAGE_STORE).upload_file(file_to_save, filename)
    print("Saved %s to s3" % filename)

if __name__ == '__main__':
    webapp.run()
