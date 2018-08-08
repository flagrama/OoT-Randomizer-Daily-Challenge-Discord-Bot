from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import shutil
import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("file_name")
    parser.add_argument("upload_dir")
    args = parser.parse_args()

    # Zip Rom and Wad
    shutil.make_archive(args.upload_dir, 'zip', args.upload_dir)

    # Authenticate
    gauth = GoogleAuth()
    gauth.LoadCredentialsFile('credentials.json')
    if gauth.credentials is None:
        gauth.LocalWebserverAuth()
    elif gauth.access_token_expired:
        gauth.Refresh()
    else:
        gauth.Authorize()
    gauth.SaveCredentialsFile('credentials.json')

    # Upload
    drive = GoogleDrive(gauth)
    upload_file = drive.CreateFile({'title': args.file_name})
    upload_file.SetContentFile(args.upload_dir + '.zip')
    upload_file.Upload()

    # Share with everyone
    upload_file['id']
    upload_file.InsertPermission({
        'type': 'anyone',
        'value': 'anyone',
        'role': 'reader'
    })

    # Create share link
    link = upload_file['alternateLink']
    link=link.split('?')[0]
    link=link.split('/')[-2]
    link='https://docs.google.com/uc?export=download&id='+link

    print(link)

if __name__ == "__main__":
    main()
