import os
import sys
import shutil
import struct
import mimetypes
import subprocess
import configparser
from tqdm import tqdm
from time import sleep
from pathlib import Path
from PyQt5 import QtWidgets, QtGui, QtCore

class QQNTEmojiExporter(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.savePath = None
        self.default_ini_path = r'C:\Users\Public\Documents\Tencent\QQ\UserDataInfo.ini'
        self.initUI()

    def initUI(self):
        self.setGeometry(300, 300, 590, 350)
        self.setWindowTitle('QQNT表情批量导出')

        layout = QtWidgets.QVBoxLayout()
        form_layout = QtWidgets.QFormLayout()

        save_path_layout = QtWidgets.QHBoxLayout()
        self.savePathEdit = QtWidgets.QLineEdit()
        self.selectDirButton = QtWidgets.QPushButton('浏览')
        self.selectDirButton.clicked.connect(self.selectSavePath)
        save_path_layout.addWidget(self.savePathEdit)
        save_path_layout.addWidget(self.selectDirButton)
        form_layout.addRow('保存路径:', save_path_layout)

        self.userComboBox = QtWidgets.QComboBox()
        form_layout.addRow('选择用户:', self.userComboBox)

        layout.addLayout(form_layout)

        self.startButton = QtWidgets.QPushButton('开始导出')
        self.startButton.clicked.connect(self.startExport)
        layout.addWidget(self.startButton)

        self.progressBar = QtWidgets.QProgressBar()
        self.progressBar.setStyleSheet("QProgressBar {border: 2px solid grey; border-radius: 5px; text-align: center; } QProgressBar::chunk {background-color: #05B8CC; width: 20px; }")
        layout.addWidget(self.progressBar)

        self.statusLabel = QtWidgets.QLabel('')
        self.statusLabel.setStyleSheet("QLabel {font-size: 16px;}")
        layout.addWidget(self.statusLabel)

        self.setLayout(layout)

        self.populateUserComboBox()

    def selectSavePath(self):
        options = QtWidgets.QFileDialog.Options()
        directory = QtWidgets.QFileDialog.getExistingDirectory(self, "选择保存路径", options=options)
        if directory:
            self.savePathEdit.setText(directory)
            self.savePath = directory

    def populateUserComboBox(self):
        configPath = self.default_ini_path
        if os.path.exists(configPath):
            userdata_save_path = self.get_userdata_save_path(configPath)
            if userdata_save_path:
                numeric_subdirs = self.get_numeric_subdirectories(userdata_save_path)
                if numeric_subdirs:
                    for subdir in numeric_subdirs:
                        self.userComboBox.addItem(subdir)
                else:
                    self.statusLabel.setText("未找到任何用户目录")
            else:
                self.statusLabel.setText("读取配置文件失败")
        else:
            self.statusLabel.setText("未找到配置文件")

    def startExport(self):
        if not self.savePath:
            self.statusLabel.setText("请先选择保存路径")
            return

        selected_user = self.userComboBox.currentText()
        if not selected_user:
            self.statusLabel.setText("请选择用户")
            return

        configPath = self.default_ini_path
        if not os.path.exists(configPath):
            self.statusLabel.setText("未找到配置文件，请手动选择")
            configPath, _ = QtWidgets.QFileDialog.getOpenFileName(self, "选择配置文件", "", "INI Files (*.ini);;All Files (*)")
            if not configPath:
                self.statusLabel.setText("请先选择配置文件")
                return

        self.statusLabel.setText("正在读取配置文件")
        userdata_save_path = self.get_userdata_save_path(configPath)
        if userdata_save_path:
            file_path = Path(os.path.join(userdata_save_path, selected_user))
            emoji_path = file_path / "nt_qq" / "nt_data" / "Emoji" / "personal_emoji" / "Ori"
            self.statusLabel.setText(f"复制表情包文件到: {self.savePath}/提取的表情")
            self.copy_directory_with_progress(str(emoji_path), self.savePath + "/提取的表情")
            self.statusLabel.setText("复制完成！开始重命名文件")
            self.batch_correct_extensions(self.savePath + "/提取的表情")
            self.statusLabel.setText("完成！正在打开输出文件夹")
            try:
                subprocess.Popen(['explorer', os.path.abspath(self.savePath + "/提取的表情")])
            except Exception as e:
                self.statusLabel.setText(f"无法打开资源管理器: {e}")
        else:
            self.statusLabel.setText("读取配置文件失败")

    def get_userdata_save_path(self, ini_file_path):
        config = configparser.ConfigParser()
        try:
            config.read(ini_file_path, encoding='utf-8')
        except UnicodeDecodeError:
            config.read(ini_file_path, encoding='gbk')
        except FileNotFoundError:
            return None
        except configparser.Error as e:
            return None

        if 'UserDataSet' not in config:
            return None

        userdata_save_path = config.get('UserDataSet', 'UserDataSavePath', fallback=None)
        return userdata_save_path

    def get_numeric_subdirectories(self, parent_dir):
        try:
            subdirs = [name for name in os.listdir(parent_dir) if os.path.isdir(os.path.join(parent_dir, name))]
            numeric_subdirs = [name for name in subdirs if name.isdigit()]
            return numeric_subdirs
        except FileNotFoundError:
            return []
        except Exception as e:
            return []

    def copy_directory_with_progress(self, src, dst):
        try:
            if not os.path.exists(src):
                return

            if not os.path.exists(dst):
                os.makedirs(dst)

            total_files = sum(len(files) for _, _, files in os.walk(src))

            self.progressBar.setMaximum(total_files)

            file_count = 0
            for root, dirs, files in os.walk(src):
                rel_path = os.path.relpath(root, src)
                dest_path = os.path.join(dst, rel_path)
                if not os.path.exists(dest_path):
                    os.makedirs(dest_path)

                for file in files:
                    src_file = os.path.join(root, file)
                    dest_file = os.path.join(dest_path, file)
                    shutil.copy2(src_file, dest_file)
                    file_count += 1
                    self.progressBar.setValue(file_count)
                    QtCore.QCoreApplication.processEvents()  # 更新进度条显示

        except Exception as e:
            self.statusLabel.setText(f"错误: {e}")

    FILE_SIGNATURES = {
        'jpg': (b'\xff\xd8\xff', b'\xff\xd8\xff\xe0', b'\xff\xd8\xff\xe1'),
        'png': (b'\x89PNG\r\n\x1a\n',),
        'gif': (b'GIF87a', b'GIF89a'),
        'bmp': (b'BM',),
        'tiff': (b'II*\x00', b'MM\x00*'),
        'webp': (b'RIFF', b'WEBP'),
        'ico': (b'\x00\x00\x01\x00', b'\x00\x00\x02\x00'),
        'psd': (b'8BPS',),
        'svg': (b'<?xml', b'<svg'),
        'heic': (b'ftypheic', b'ftypheix', b'ftyphevc', b'ftyphevx'),
        'avif': (b'ftypavif', b'ftypavis'),
    }

    MIME_MAPPING = {
        'jpg': 'image/jpeg',
        'png': 'image/png',
        'gif': 'image/gif',
        'bmp': 'image/bmp',
        'tiff': 'image/tiff',
        'webp': 'image/webp',
        'ico': 'image/x-icon',
        'psd': 'image/vnd.adobe.photoshop',
        'svg': 'image/svg+xml',
        'heic': 'image/heic',
        'avif': 'image/avif',
    }

    def get_actual_extension(self, file_path):
        with open(file_path, 'rb') as f:
            header = f.read(16)

        for ext, signatures in self.FILE_SIGNATURES.items():
            for sig in signatures:
                if header.startswith(sig):
                    return ext
        return None

    def get_recommended_extension(self, file_path):
        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type:
            for ext, mt in self.MIME_MAPPING.items():
                if mt == mime_type:
                    return ext
        return None

    def correct_file_extension(self, file_path):
        actual_ext = self.get_actual_extension(file_path)
        if not actual_ext:
            return

        recommended_ext = self.get_recommended_extension(file_path)
        if recommended_ext:
            if actual_ext.lower() != recommended_ext.lower():
                base_name, _ = os.path.splitext(file_path)
                new_file_path = f"{base_name}.{actual_ext}"
                if os.path.exists(new_file_path):
                    return
                try:
                    os.rename(file_path, new_file_path)
                except Exception as e:
                    return
    def correct_file_extension(self, file_path):
            actual_ext = self.get_actual_extension(file_path)
            if not actual_ext:
                return

            recommended_ext = self.get_recommended_extension(file_path)
            if recommended_ext:
                if actual_ext.lower() != recommended_ext.lower():
                    base_name, _ = os.path.splitext(file_path)
                    new_file_path = f"{base_name}.{actual_ext}"
                    if os.path.exists(new_file_path):
                        return
                    try:
                        os.rename(file_path, new_file_path)
                    except Exception as e:
                        return

    def batch_correct_extensions(self, directory):
        for root, dirs, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)
                mime_type, _ = mimetypes.guess_type(file_path)
                if mime_type and mime_type.startswith('image/'):
                    self.correct_file_extension(file_path)


def main():
    app = QtWidgets.QApplication(sys.argv)
    ex = QQNTEmojiExporter()
    ex.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
