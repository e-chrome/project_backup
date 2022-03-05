import requests
import os
from datetime import datetime
from progress.bar import IncrementalBar
version_api_vk = '5.131'


class YaUploader:
    def __init__(self, token):
        self.token = token

    def upload(self, file_path, file):
        try:
            href = self._get_upload_link(disk_file_path=file_path).get("href", "")
            if href == '':
                print('Загрузка завершилась ошибкой!')
                return
            response = requests.put(href, data=file, timeout=5)
            response.raise_for_status()
            if response.status_code != 201:
                print("Ошибка загрузки!")
        except:
            print('Загрузка завершилась ошибкой!')

    def _get_headers(self):
        return {
            'Content-Type': 'application/json',
            'Authorization': 'OAuth {}'.format(self.token)
        }

    def _get_upload_link(self, disk_file_path):
        try:
            upload_url = "https://cloud-api.yandex.net/v1/disk/resources/upload"
            headers = self._get_headers()
            params = {"path": disk_file_path, "overwrite": "true"}
            response = requests.get(upload_url, headers=headers, params=params, timeout=5)
            response.raise_for_status()
            if response.status_code == 200:
                return response.json()
            else:
                print('Не удалось получить ссылку для загрузки фото!')
                return {}
        except:
            print('Не удалось получить ссылку для загрузки фото!')
            return {}


class VkPhotoGetter:
    def __init__(self, token, version):
        self.token = token
        self.version = version

    def get_photo_list(self):
        photo_list = []
        url = 'https://api.vk.com/method/photos.get'
        params = {
            'access_token': self.token,
            'owner_id': '97290691',
            'album_id': 'profile',
            'extended': '1',
            'photo_sizes': '1',
            'count': '100',
            'v': self.version
        }
        try:
            response = requests.get(url, params=params, timeout=5)
            response.raise_for_status()
            if response.status_code != 200:
                print('Не удалось получить список фотографий из Vk')
                quit()
            for photo in response.json()['response']['items']:
                processed_photo = self._find_max_photo(photo)
                processed_photo = self._to_name_photo(response, processed_photo)
                photo_list.append(processed_photo)
                # сортируем список фотографий по размеру в пикселях, чтобы скачивать фотографии по порядку согласно ФТ
                sorted_photo_list = sorted(photo_list, key=lambda item: item['size'], reverse=True)
            return sorted_photo_list
        except:
            print('Работа с API VK завершилась ошибкой!')
            quit()

    def _find_max_photo(self, photo):
        # ищем для каждой фотографии вариант максимального размера и оставляем только его
        int_max_size = 0
        target_size = photo['sizes'][0]
        for size in photo['sizes']:
            int_current_size = size['height'] * size['width']
            if int_current_size > int_max_size:
                int_max_size = int_current_size
                target_size = size
        photo.pop('sizes', '')
        photo['size'] = target_size['height'] * target_size['width']
        photo['url'] = target_size['url']
        photo['date'] = datetime.fromtimestamp(photo['date']).strftime('%d-%m-%Y')
        return photo

    def _to_name_photo(self, response, photo):
        # присваиваем фотографии в качестве имени количество лайков. Если значения повторяются,
        # добавляем к имени дату
        likes_repetition = 0
        for item in response.json()['response']['items']:
            if photo['likes']['count'] == item['likes']['count']:
                likes_repetition += 1
        if likes_repetition > 1:
            photo['name'] = str(photo['likes']['count']) + '_' + photo['date']
        else:
            photo['name'] = str(photo['likes']['count'])
        return photo


def download_photo_from_vk(photo_list):
    try:
        quantity = int(input('Введите количество фото для скачивания: '))
    except TypeError:
        print('Нужно ввести целое число!')
    if quantity < 1:
        pass
    else:
        bar = IncrementalBar('Осталось ', max=quantity)
        info_list = []
        for photo in photo_list[0:quantity]:
            info_dict = {}
            try:
                with open('pictures/' + photo['name'] + '.jpg', 'wb') as f:
                    picture = requests.get(photo['url'])
                    f.write(picture.content)
                info_dict['file_name'] = photo['name'] + '.jpg'
                info_dict['size'] = photo['size']
                info_list.append(info_dict)
            except:
                print('Не удалось загрузить фото!')
            bar.next()
        bar.finish()
        with open('info.json', 'w') as f:
            f.write(str(info_list))


def put_photo_on_ya_disk_from_pc(uploader, path='/api_vk/'):
    files = os.listdir('pictures/')
    bar = IncrementalBar('Осталось ', max=len(files))
    for file in files:
        with open('pictures/' + file, 'rb') as f:
            uploader.upload(path + file, f)
        bar.next()
    bar.finish()


def put_photo_on_ya_disk_from_vk(photo_list, uploader, path='/api_vk/'):
    try:
        quantity = int(input('Введите количество фото для загрузки на Яндекс Диск: '))
    except TypeError:
        print('Нужно ввести целое число!')
    if quantity < 1:
        pass
    else:
        bar = IncrementalBar('Осталось ', max=quantity)
        info_list = []
        for photo in photo_list[0:quantity]:
            info_dict = {}
            try:
                picture = requests.get(photo['url'])
                uploader.upload(path + photo['name'] + '.jpg', picture.content)
                info_dict['file_name'] = photo['name'] + '.jpg'
                info_dict['size'] = photo['size']
                info_list.append(info_dict)
            except:
                print('Не удалось загрузить фото!')
            bar.next()
        bar.finish()
        with open('info.json', 'w') as f:
            f.write(str(info_list))


def clear_directory(directory):
    files = os.listdir(directory)
    for file in files:
        os.remove(directory + file)


if __name__ == '__main__':

    with open('tokens/ya_disk_token.txt') as f:
        ya_disk_token = f.read().strip()
    with open('tokens/vk_token.txt') as f:
        vk_token = f.read().strip()

    getter = VkPhotoGetter(vk_token, version_api_vk)
    photo_list = getter.get_photo_list()
    uploader = YaUploader(ya_disk_token)

    while True:
        text = '''Выберите команду:
        1 - скачать фото из ВК в папку \'pictures\'
        2 - загрузить фото из папки \'pictures\' на Яндекс Диск
        3 - очистить папку \'pictures\'
        4 - загрузить фото из ВК напрямую на Яндекс Диск
        5 - выйти из программы'''
        print(text)
        command = input('Ввод: ')

        if command == '1':
            clear_directory('pictures/')
            download_photo_from_vk(photo_list)
        elif command == '2':
            put_photo_on_ya_disk_from_pc(uploader, path='/api_vk/')
        elif command == '3':
            clear_directory('pictures/')
        elif command == '4':
            put_photo_on_ya_disk_from_vk(photo_list, uploader, path='/api_vk/')
        elif command == '5':
            break
        else:
            print('Введена некорректная команда!')

