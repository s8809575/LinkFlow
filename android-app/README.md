# LinkFlow Android App

基于 WebView 的 LinkFlow 手机端应用，将 HTML 功能封装为原生 Android APK。

## 项目结构

```
android-app/
├── app/
│   ├── src/main/
│   │   ├── java/com/linkflow/app/
│   │   │   └── MainActivity.kt    ← WebView 封装代码
│   │   ├── res/
│   │   │   ├── layout/            ← 布局文件
│   │   │   ├── values/            ← 字符串、颜色、主题
│   │   │   └── drawable/          ← 图标资源
│   │   └── assets/
│   │       ├── index.html         ← (请复制您的 HTML 文件到这里)
│   │       └── js/                ← (请复制您的 JS 文件到这里)
│   └── build.gradle
├── build.gradle
└── settings.gradle
```

## 使用步骤

### 1. 复制 HTML 文件

将您的 HTML 项目文件复制到 `app/src/main/assets/` 目录：

```
app/src/main/assets/
├── index.html      ← 从 src/web/mobile/index.html 复制
└── js/
    └── mobile_app.js  ← 从 src/web/mobile/js/ 复制
```

### 2. 用 Android Studio 打开项目

1. 打开 Android Studio
2. 选择 `File` → `Open`
3. 选择 `src/android-app` 文件夹
4. 点击 `OK`

### 3. 等待 Gradle 同步完成

首次打开会下载依赖，需要几分钟时间。

### 4. 运行项目

1. 连接手机或启动模拟器
2. 点击 Android Studio 的 ▶️ `Run` 按钮
3. APK 会自动安装并启动

### 5. 构建 release 版本

```bash
cd src/android-app
./gradlew assembleRelease
```

APK 输出位置：`app/build/outputs/apk/release/app-release.apk`

## 前提条件

- Android Studio Hedgehog (2023.11) 或更新版本
- JDK 17+
- Android SDK 34

## 功能特性

- ✅ WebView 封装，保持 HTML 功能完整
- ✅ 加载动画，提升用户体验
- ✅ JavaScript 和 DOM 存储支持
- ✅ 文件访问权限
- ✅ 返回键处理（可返回上一页）
- ✅ 自动申请网络权限

## 注意事项

- 确保 `assets/index.html` 存在且路径正确
- 如果 HTML 中有外部资源引用，请确保 assets 目录结构匹配
- release 版本需要签名配置，可使用 Android Studio 的签名向导生成
