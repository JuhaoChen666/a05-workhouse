# 移动端开发工程师(Android)知识库

## 一、Android基础

### 1.1 四大组件

#### Activity
Activity是Android应用程序的界面组件，负责与用户交互。

**生命周期：**
- onCreate()：创建时调用，初始化UI
- onStart()：可见但不可交互
- onResume()：可见且可交互（前台）
- onPause()：失去焦点但仍可见
- onStop()：不可见
- onRestart()：从停止状态重新启动
- onDestroy()：销毁

**启动模式：**
- standard：标准模式，每次创建新实例
- singleTop：栈顶复用，否则创建新实例
- singleTask：栈内复用，清空其上所有Activity
- singleInstance：独立任务栈，全局唯一

**任务栈：**
- 任务（Task）是Activity的集合，以栈形式管理
- 最近任务列表显示各任务的最新Activity
- 可通过taskAffinity指定任务归属

#### Service
Service用于在后台执行长时间运行操作，不提供用户界面。

**启动方式：**
- startService()：启动服务，服务独立运行，需手动停止
- bindService()：绑定服务，组件与服务交互，解绑后销毁

**生命周期：**
- onCreate() → onStartCommand() → onDestroy()
- onCreate() → onBind() → onUnbind() → onDestroy()

**前台服务：**
- 必须显示通知
- 优先级高，不易被系统杀死
- 适用于需要持续运行的任务

#### BroadcastReceiver
广播接收器用于接收系统或应用发送的广播消息。

**注册方式：**
- 静态注册：AndroidManifest.xml中声明
- 动态注册：代码中registerReceiver()

**广播类型：**
- 有序广播：按优先级顺序接收，可拦截
- 无序广播：同时接收，无法拦截
- 本地广播：仅应用内传播，效率高（LocalBroadcastManager）

#### ContentProvider
内容提供者用于在不同应用间共享数据。

**特点：**
- 统一的数据访问接口
- 支持跨进程数据共享
- 实现数据访问权限控制
- 底层基于Binder机制

**URI格式：**
```
content://com.example.provider/table_name/id
```

### 1.2 Intent与IntentFilter

#### Intent
Intent用于组件间的通信，可启动Activity、Service、发送广播。

**分类：**
- 显式Intent：明确指定目标组件
- 隐式Intent：通过Action、Category、Data匹配

**属性：**
- Action：动作类型
- Data：操作数据URI
- Category：类别
- Type：MIME类型
- Component：目标组件
- Extras：附加数据
- Flags：启动标志

#### IntentFilter
用于声明组件可响应的隐式Intent。

**匹配规则：**
- Action匹配：Intent的Action必须在Filter中
- Category匹配：Intent的所有Category必须在Filter中
- Data匹配：Scheme、Host、Port、Path、Type匹配

### 1.3 上下文Context

Context是Android中访问系统资源和服务的接口。

**分类：**
- Application Context：应用全局上下文，生命周期同应用
- Activity Context：Activity上下文，生命周期同Activity
- Service Context：Service上下文

**使用注意：**
- 避免Activity Context泄漏（如单例持有）
- 长时间引用使用Application Context
- UI相关操作需要Activity Context

---

## 二、Android UI

### 2.1 View体系

#### View与ViewGroup
- View：UI组件的基本单元，负责绘制和事件处理
- ViewGroup：View的容器，负责子View的测量、布局、绘制

**测量模式：**
- EXACTLY：精确值（match_parent或具体值）
- AT_MOST：最大值（wrap_content）
- UNSPECIFIED：无限制（ListView等）

**绘制流程：**
1. measure()：测量View大小
2. layout()：确定View位置
3. draw()：绘制View内容

#### 自定义View

**方式：**
- 继承现有View：扩展功能
- 继承View：完全自定义绘制
- 继承ViewGroup：自定义布局

**关键方法：**
- onMeasure()：测量
- onLayout()：布局（ViewGroup）
- onDraw()：绘制
- onTouchEvent()：触摸事件
- onInterceptTouchEvent()：事件拦截（ViewGroup）

**优化：**
- 减少onDraw()中对象创建
- 使用Canvas.clipRect()局部绘制
- 开启硬件加速

### 2.2 布局

#### 常用布局
- LinearLayout：线性排列
- RelativeLayout：相对定位
- FrameLayout：层叠布局
- ConstraintLayout：约束布局（推荐）
- CoordinatorLayout：协调布局

#### ConstraintLayout
- 通过约束条件定位子View
- 减少布局层级，提升性能
- 支持百分比、链条、引导线

#### 布局优化
- 使用ConstraintLayout减少层级
- 使用merge标签减少冗余
- 使用ViewStub延迟加载
- 避免过度绘制

### 2.3 RecyclerView

#### 核心组件
- Adapter：数据适配
- ViewHolder：视图复用
- LayoutManager：布局管理
- ItemDecoration：分割线/间距
- ItemAnimator：动画

#### 优化策略
- 固定ItemView高度（setHasFixedSize）
- 使用DiffUtil局部更新
- 分页加载（Paging）
- 缓存优化（setItemViewCacheSize）
- 避免onBindViewHolder中复杂操作

### 2.4 动画

#### 属性动画（Property Animation）
- ValueAnimator：值动画
- ObjectAnimator：对象属性动画
- AnimatorSet：动画组合

**特点：**
- 改变真实属性值
- 可作用于任意对象
- 支持插值器和估值器

#### 视图动画（View Animation）
- AlphaAnimation：透明度
- ScaleAnimation：缩放
- TranslateAnimation：平移
- RotateAnimation：旋转

**特点：**
- 仅改变视觉效果
- 不改变真实属性
- 执行后点击位置不变

#### 过渡动画
- Activity过渡：共享元素、Explode、Slide、Fade
- Fragment过渡
- 转场动画API（Transition Framework）

---

## 三、Android存储

### 3.1 数据存储方式

#### SharedPreferences
- 轻量级键值对存储
- 存储在/data/data/package/shared_prefs/
- 适合存储简单配置

**优化：**
- 使用apply()异步提交
- 批量修改使用Editor
- 避免存储大数据
- 考虑MMKV替代

#### 内部存储
- /data/data/package/files/
- 应用私有，其他应用无法访问
- 适合存储应用私有文件

#### 外部存储
- 公有目录：Pictures、Downloads等
- 私有目录：Android/data/package/
- Android 10+分区存储限制

#### SQLite
- 轻量级关系型数据库
- 使用SQLiteOpenHelper管理
- Room是官方ORM框架

### 3.2 Room数据库

#### 核心组件
- Entity：数据表实体
- DAO：数据访问对象
- Database：数据库持有者

**特性：**
- 编译时SQL检查
- 支持LiveData、Flow观察
- 支持事务
- 支持数据库迁移

### 3.3 数据序列化

#### Serializable
- Java标准接口
- 使用反射，性能较差
- 产生大量临时对象

#### Parcelable
- Android专用接口
- 手动实现，性能高
- 推荐使用

---

## 四、Android网络

### 4.1 网络请求

#### HttpURLConnection
- Android原生HTTP客户端
- 支持HTTPS、缓存、Cookie

#### OkHttp
- Square开源HTTP客户端
- 连接池复用
- 拦截器机制
- GZIP压缩
- 响应缓存

**核心组件：**
- OkHttpClient：客户端配置
- Request：请求构建
- Call：请求执行
- Response：响应结果
- Interceptor：拦截器

#### Retrofit
- Square开源REST客户端
- 基于OkHttp
- 注解定义API
- 支持多种数据转换器

**注解：**
- @GET、@POST、@PUT、@DELETE：HTTP方法
- @Path：URL路径参数
- @Query：查询参数
- @Body：请求体
- @Header：请求头

### 4.2 图片加载

#### Glide
- Google推荐图片加载库
- 支持GIF、WebP、视频缩略图
- 内存和磁盘缓存
- 图片变换

**缓存策略：**
- 内存缓存：LruCache
- 磁盘缓存：DiskLruCache
- 活动资源：弱引用缓存

#### 图片优化
- 使用合适尺寸（inSampleSize采样）
- 使用RGB_565减少内存
- 复用Bitmap（inBitmap）
- 及时回收（Bitmap.recycle()）

### 4.3 数据解析

#### JSON解析
- Gson：Google出品，注解支持
- Jackson：功能丰富，性能高
- Moshi：Square出品，Kotlin友好
- org.json：Android原生

#### XML解析
- DOM：内存占用大
- SAX：事件驱动，逐行解析
- Pull：Android推荐，类似SAX

---

## 五、Android多线程

### 5.1 线程基础

#### 主线程（UI线程）
- 负责UI更新和事件处理
- 不能执行耗时操作（ANR）
- 子线程不能更新UI

#### ANR
Application Not Responding，应用无响应。

**触发条件：**
- 主线程5秒内未响应输入事件
- BroadcastReceiver 10秒内未完成
- Service 20秒内未完成

**避免：**
- 耗时操作放子线程
- 使用异步机制

### 5.2 异步机制

#### Handler机制
Android消息处理机制的核心。

**核心类：**
- Handler：发送和处理消息
- Looper：消息循环器
- MessageQueue：消息队列
- Message：消息载体

**流程：**
1. Looper.prepare()创建Looper和MessageQueue
2. Handler发送Message到MessageQueue
3. Looper.loop()循环取出消息
4. Handler.handleMessage()处理消息

#### AsyncTask（已弃用）
轻量级异步任务，串行执行（API 11+）。

**替代方案：**
- HandlerThread
- ThreadPoolExecutor
- Kotlin Coroutines
- RxJava

#### HandlerThread
- 自带Looper的工作线程
- 适合需要消息循环的后台任务

#### IntentService
- 基于Service的异步处理
- 工作线程执行，完成后自动停止
- 适合一次性后台任务

### 5.3 线程池

#### ThreadPoolExecutor
Java标准线程池。

**参数：**
- corePoolSize：核心线程数
- maximumPoolSize：最大线程数
- keepAliveTime：非核心线程存活时间
- workQueue：任务队列
- threadFactory：线程工厂
- handler：拒绝策略

**Executors工厂方法：**
- newFixedThreadPool：固定线程数
- newCachedThreadPool：可缓存线程
- newSingleThreadExecutor：单线程
- newScheduledThreadPool：定时任务

### 5.4 Kotlin协程

#### 协程基础
- 轻量级线程，由Kotlin管理
- 挂起函数（suspend）
- 非阻塞式异步编程

**核心组件：**
- CoroutineScope：协程作用域
- CoroutineContext：协程上下文
- Dispatcher：调度器（Dispatchers.Main、IO、Default）
- Job：协程任务
- Deferred：带返回值的Job

#### 协程使用
```kotlin
// 启动协程
GlobalScope.launch { }
lifecycleScope.launch { }
viewModelScope.launch { }

// 挂起函数
suspend fun fetchData(): String { }

// 异步并发
val deferred1 = async { fetchData1() }
val deferred2 = async { fetchData2() }
val result = deferred1.await() + deferred2.await()
```

---

## 六、Android架构

### 6.1 MVP
Model-View-Presenter架构。

**角色：**
- Model：数据层
- View：UI层（Activity/Fragment）
- Presenter：逻辑层，连接View和Model

**特点：**
- View和Model完全隔离
- Presenter持有View接口
- 便于单元测试
- 接口过多，代码冗余

### 6.2 MVVM
Model-View-ViewModel架构（Google推荐）。

**角色：**
- Model：数据层
- View：UI层
- ViewModel：业务逻辑，不持有View引用

**特点：**
- 数据驱动UI
- 使用DataBinding或LiveData
- ViewModel生命周期感知
- 便于测试和维护

### 6.3 Jetpack组件

#### ViewModel
- 生命周期感知
- 配置变更（旋转屏幕）后数据保留
- 不持有View引用

#### LiveData
- 可观察数据持有者
- 生命周期感知，自动管理订阅
- 避免内存泄漏

#### DataBinding
- 布局中绑定数据
- 减少findViewById
- 支持双向绑定

#### Lifecycle
- 生命周期管理
- LifecycleOwner、LifecycleObserver

#### Navigation
- 单Activity多Fragment导航
- 可视化导航图
- 支持深层链接

#### Paging
- 分页加载数据
- 支持Room、网络数据源

#### WorkManager
- 后台任务调度
- 保证任务执行
- 支持约束条件

### 6.4 依赖注入

#### Hilt
Google官方依赖注入框架，基于Dagger。

**注解：**
- @HiltAndroidApp：Application入口
- @AndroidEntryPoint：组件入口
- @Inject：注入依赖
- @Module：提供依赖模块
- @Provides：提供实例
- @Singleton：单例

---

## 七、Android性能优化

### 7.1 内存优化

#### 内存泄漏
对象不再使用但无法被GC回收。

**常见原因：**
- 静态变量持有Activity
- 匿名内部类持有外部类引用
- 未取消注册监听器/广播
- Handler延迟消息持有Activity
- 资源未关闭（Cursor、File等）

**检测工具：**
- LeakCanary
- Android Studio Profiler
- MAT（Memory Analyzer Tool）

#### OOM
Out Of Memory，内存溢出。

**原因：**
- 加载大图
- 内存泄漏累积
- 大量对象创建

**解决：**
- Bitmap压缩和复用
- 使用LruCache
- 及时释放资源

#### 内存抖动
短时间内大量对象创建和销毁。

**解决：**
- 避免onDraw中创建对象
- 使用对象池
- 使用StringBuilder替代String拼接

### 7.2 UI优化

#### 布局优化
- 减少布局层级（ConstraintLayout）
- 使用merge标签
- 使用ViewStub延迟加载
- 避免过度绘制

#### 绘制优化
- 减少onDraw中计算
- 使用Canvas.clipRect局部绘制
- 开启硬件加速

#### 卡顿优化
- 避免主线程耗时操作
- 使用RecyclerView替代ListView
- 懒加载和分页加载
- 使用Systrace、Choreographer检测卡顿

### 7.3 启动优化

#### 冷启动
应用首次启动，需要创建进程。

**优化：**
- 延迟初始化（懒加载）
- 异步初始化（子线程）
- 使用ContentProvider延迟初始化
- 优化Application.onCreate()
- 使用SplashTheme避免白屏

#### 热启动
应用从后台回到前台。

### 7.4 APK瘦身

**方法：**
- 资源混淆（AndResGuard）
- 图片压缩（WebP、TinyPNG）
- 移除无用资源（lint）
- 代码混淆（ProGuard/R8）
- 只保留必要ABI（so库）
- 使用Android App Bundle

---

## 八、Android安全

### 8.1 代码安全

#### 代码混淆
- ProGuard/R8混淆类名、方法名
- 移除无用代码
- 字符串加密

#### 加固
- 加壳保护
- 反调试、反模拟器
- 签名校验

### 8.2 数据安全

#### 存储安全
- SharedPreferences使用MODE_PRIVATE
- 敏感数据加密存储（AES、RSA）
- 密钥安全存储（Android Keystore）

#### 传输安全
- HTTPS通信
- 证书校验（防止中间人攻击）
- 敏感数据加密传输

### 8.3 权限管理

#### 权限分类
- 普通权限：安装时自动授予
- 危险权限：运行时动态申请

#### 运行时权限（Android 6.0+）
- 检查权限：checkSelfPermission()
- 申请权限：requestPermissions()
- 处理回调：onRequestPermissionsResult()

---

## 九、Android系统机制

### 9.1 Binder机制

Android进程间通信（IPC）机制。

**特点：**
- 基于C/S架构
- 一次内存拷贝（优于管道、Socket）
- 支持实名和匿名Binder

**组成：**
- Binder驱动：内核层
- ServiceManager：管理Service注册和查询
- Binder客户端/服务端：应用层

### 9.2 AMS与WMS

#### AMS（ActivityManagerService）
- 管理Activity、Service生命周期
- 管理进程和任务栈
- 调度组件启动

#### WMS（WindowManagerService）
- 管理窗口的添加、删除、更新
- 计算窗口大小和位置
- 管理窗口层级（Z-order）

### 9.3 消息机制

#### Looper
- 创建MessageQueue
- loop()循环取出消息
- 每个线程只能有一个Looper

#### Handler
- 发送消息到MessageQueue
- 处理消息回调

#### MessageQueue
- 单链表结构
- 按时间排序
- nativePollOnce阻塞等待

### 9.4 屏幕刷新机制

#### Choreographer
- 协调动画、输入、绘制
- 接收VSync信号
- 控制UI刷新节奏

#### VSync
- 垂直同步信号
- 60fps约16.6ms一帧
- 避免画面撕裂

#### 三重缓冲
- 减少丢帧，提升流畅度
- Front Buffer、Back Buffer、Triple Buffer

---

## 十、Android新技术

### 10.1 Jetpack Compose

Google声明式UI框架。

**特点：**
- 声明式编程
- Kotlin DSL
- 实时预览
- 状态驱动UI

**核心概念：**
- Composable：可组合函数
- State：状态
- Modifier：修饰符
- SideEffect：副作用

### 10.2 Kotlin

#### 协程
见5.4节

#### Flow
- 响应式流
- 冷流（Cold Flow）
- 热流（StateFlow、SharedFlow）

#### 其他特性
- 扩展函数
- 高阶函数
- 空安全
- 数据类（data class）
- 密封类（sealed class）

### 10.3 Flutter

Google跨平台UI框架。

**特点：**
- 单一代码库（Dart）
- 自绘引擎（Skia）
- 高性能
- 热重载

**架构：**
- Framework层（Dart）
- Engine层（C++）
- Embedder层（平台相关）

### 10.4 模块化与动态化

#### 组件化
- 业务模块独立
- 模块间解耦
- ARouter路由通信

#### 插件化
- 动态加载dex
- 热修复
- 免安装运行

#### App Bundle
- Google Play动态交付
- 按需下载功能模块
- 按设备配置分发

---

## 十一、常用第三方库

### 网络
- OkHttp：HTTP客户端
- Retrofit：REST客户端
- Volley：Google网络库

### 图片
- Glide：图片加载
- Picasso：Square图片加载
- Fresco：Facebook图片加载
- Coil：Kotlin协程图片加载

### 响应式
- RxJava：响应式编程
- Kotlin Coroutines：协程
- LiveData：生命周期感知数据

### 依赖注入
- Dagger2：编译时注入
- Hilt：Dagger封装
- Koin：Kotlin轻量级注入

### 数据库
- Room：官方ORM
- GreenDAO：高性能ORM
- Realm：移动端数据库

### 其他
- EventBus：事件总线
- ButterKnife：View绑定（已弃用）
- LeakCanary：内存泄漏检测
- Timber：日志框架
