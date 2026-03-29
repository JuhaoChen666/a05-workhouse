# 移动端开发工程师(Android)问题库

> 难度系数说明：
> - 0-0.3：基础概念
> - 0.3-0.6：原理探究
> - 0.6-0.9：场景应用
> - 0.9-1.0：极限深挖

---

## 一、Android基础

### 1.1 四大组件

#### 问题1：Android四大组件是什么？
- **难度系数**：0.15
- **追问深度**：基础概念
- **参考答案**：Activity（界面交互）、Service（后台服务）、BroadcastReceiver（广播接收）、ContentProvider（数据共享）。
- **评分关键词**：Activity、Service、BroadcastReceiver、ContentProvider、界面、后台、广播、共享

#### 问题2：Activity的生命周期有哪些？
- **难度系数**：0.2
- **追问深度**：基础概念
- **参考答案**：onCreate（创建初始化）→ onStart（可见）→ onResume（可交互）→ onPause（失去焦点）→ onStop（不可见）→ onRestart（重新启动）→ onDestroy（销毁）。
- **评分关键词**：onCreate、onStart、onResume、onPause、onStop、onDestroy、可见、可交互

#### 问题3：Activity的启动模式有哪些？
- **难度系数**：0.25
- **追问深度**：基础概念
- **参考答案**：standard（标准，每次新建）、singleTop（栈顶复用）、singleTask（栈内复用，清空其上Activity）、singleInstance（独立任务栈，全局唯一）。
- **评分关键词**：standard、singleTop、singleTask、singleInstance、栈顶、任务栈

#### 问题4：你能举个例子说明singleTask的使用场景吗？
- **难度系数**：0.3
- **追问深度**：基础概念
- **参考答案**：例如首页Activity，从任何页面点击返回首页都应该是同一个实例，且清空中间页面。设置singleTask后，启动首页时会将任务栈中其上所有Activity出栈，保证首页在栈底。
- **评分关键词**：首页、同一个实例、清空、栈底、任务栈

#### 问题5：为什么singleInstance要保证全局唯一？如果线程数超过CPU核心数，上下文调度具体怎么实现的？
- **难度系数**：0.95
- **追问深度**：极限深挖
- **参考答案**：singleInstance会在新的任务栈中创建Activity，且该任务栈中只有这一个Activity。Android系统通过ActivityRecord和TaskRecord管理Activity和任务栈，singleInstance的Activity有独立的affinity，系统会查找是否存在该affinity的任务栈，存在则复用，不存在则新建。Android线程调度基于Linux的CFS（完全公平调度器），使用红黑树管理可运行线程，通过时间片轮转调度。当线程数超过CPU核心数时，线程在运行队列中等待，上下文切换时保存/恢复寄存器状态。
- **评分关键词**：任务栈、ActivityRecord、affinity、红黑树、CFS、时间片、上下文切换

#### 问题6：Service的生命周期是怎样的？
- **难度系数**：0.25
- **追问深度**：基础概念
- **参考答案**：startService方式：onCreate → onStartCommand → onDestroy；bindService方式：onCreate → onBind → onUnbind → onDestroy。两种方式混合使用时，需stopService和unbindService都调用才会销毁。
- **评分关键词**：onCreate、onStartCommand、onBind、onUnbind、onDestroy、startService、bindService

#### 问题7：Service和IntentService有什么区别？
- **难度系数**：0.35
- **追问深度**：原理探究
- **参考答案**：Service运行在主线程，需手动处理耗时操作和停止；IntentService继承Service，内部使用HandlerThread创建工作线程，顺序处理任务，完成后自动停止。IntentService适合一次性后台任务，Service适合长期运行服务。
- **评分关键词**：主线程、HandlerThread、工作线程、自动停止、顺序处理

#### 问题8：前台服务和后台服务有什么区别？
- **难度系数**：0.3
- **追问深度**：基础概念
- **参考答案**：前台服务必须显示通知，优先级高，系统不会轻易杀死；后台服务优先级低，内存不足时可能被杀死。Android 8.0+对后台服务限制更严格，推荐使用WorkManager。
- **评分关键词**：通知、优先级、杀死、Android 8.0、WorkManager

#### 问题9：BroadcastReceiver的注册方式有哪些？
- **难度系数**：0.25
- **追问深度**：基础概念
- **参考答案**：静态注册（AndroidManifest.xml中声明，应用未启动也可接收，Android 8.0+对隐式广播限制）和动态注册（代码中registerReceiver，需手动unregister，生命周期可控）。
- **评分关键词**：静态注册、动态注册、AndroidManifest、unregister、生命周期

#### 问题10：ContentProvider的作用是什么？
- **难度系数**：0.3
- **追问深度**：基础概念
- **参考答案**：ContentProvider用于在不同应用间共享数据，提供统一的数据访问接口，实现权限控制。底层基于Binder机制，数据访问通过URI定位。
- **评分关键词**：数据共享、跨应用、URI、Binder、权限控制

---

### 1.2 Intent与IntentFilter

#### 问题11：显式Intent和隐式Intent有什么区别？
- **难度系数**：0.2
- **追问深度**：基础概念
- **参考答案**：显式Intent明确指定目标组件（setComponent/setClass），用于应用内跳转；隐式Intent通过Action、Category、Data匹配，由系统选择合适的组件，可用于跨应用。
- **评分关键词**：显式、隐式、Component、Action、Category、跨应用

#### 问题12：IntentFilter的匹配规则是什么？
- **难度系数**：0.4
- **追问深度**：原理探究
- **参考答案**：Action匹配（Intent的Action必须在Filter中）、Category匹配（Intent的所有Category必须在Filter中）、Data匹配（Scheme、Host、Port、Path、Type匹配）。三者都匹配成功才能启动组件。
- **评分关键词**：Action、Category、Data、Scheme、匹配规则

---

### 1.3 上下文Context

#### 问题13：Context有哪些类型？有什么区别？
- **难度系数**：0.35
- **追问深度**：原理探究
- **参考答案**：Application Context（应用全局，生命周期同应用）、Activity Context（Activity上下文，生命周期同Activity）、Service Context。Activity Context持有Activity引用，可能导致内存泄漏，长时间引用应使用Application Context。
- **评分关键词**：Application Context、Activity Context、生命周期、内存泄漏

#### 问题14：单例模式中应该使用哪种Context？
- **难度系数**：0.5
- **追问深度**：原理探究
- **参考答案**：单例应使用Application Context。如果使用Activity Context，单例生命周期长于Activity，会导致Activity无法被回收，造成内存泄漏。Application Context生命周期同应用，不会导致泄漏。
- **评分关键词**：Application Context、Activity Context、内存泄漏、生命周期

---

## 二、Android UI

### 2.1 View体系

#### 问题15：View的绘制流程是怎样的？
- **难度系数**：0.4
- **追问深度**：原理探究
- **参考答案**：measure（测量View大小，从根View递归测量子View）→ layout（确定位置，父View确定子View位置）→ draw（绘制，包括背景、内容、子View、装饰）。
- **评分关键词**：measure、layout、draw、测量、位置、绘制、递归

#### 问题16：MeasureSpec是什么？
- **难度系数**：0.45
- **追问深度**：原理探究
- **参考答案**：MeasureSpec是View测量规格，由32位int表示，高2位是模式（EXACTLY精确值、AT_MOST最大值、UNSPECIFIED无限制），低30位是尺寸。父View根据LayoutParams和自身MeasureSpec计算子View的MeasureSpec。
- **评分关键词**：MeasureSpec、EXACTLY、AT_MOST、UNSPECIFIED、模式、尺寸

#### 问题17：自定义View有哪几种方式？
- **难度系数**：0.35
- **追问深度**：基础概念
- **参考答案**：1)继承现有View（如继承TextView扩展功能）；2)继承View（完全自定义绘制，需重写onMeasure、onDraw）；3)继承ViewGroup（自定义布局，需重写onMeasure、onLayout）。
- **评分关键词**：继承View、继承ViewGroup、onMeasure、onDraw、onLayout

#### 问题18：自定义View如何优化性能？
- **难度系数**：0.6
- **追问深度**：场景应用
- **参考答案**：1)减少onDraw中对象创建；2)使用Canvas.clipRect局部绘制；3)开启硬件加速；4)避免过度绘制；5)使用ViewStub延迟加载复杂布局；6)固定View大小减少测量次数。
- **评分关键词**：onDraw、clipRect、硬件加速、过度绘制、ViewStub

#### 问题19：View的事件分发机制是怎样的？
- **难度系数**：0.55
- **追问深度**：原理探究
- **参考答案**：事件从Activity→Window→DecorView→子View传递。dispatchTouchEvent分发事件，onInterceptTouchEvent判断是否拦截（ViewGroup），onTouchEvent处理事件。返回true表示消费事件，false继续传递。
- **评分关键词**：dispatchTouchEvent、onInterceptTouchEvent、onTouchEvent、分发、拦截、消费

#### 问题20：如何解决滑动冲突？
- **难度系数**：0.65
- **追问深度**：场景应用
- **参考答案**：1)外部拦截法（父View在onInterceptTouchEvent中判断拦截）；2)内部拦截法（子View在onTouchEvent中调用requestDisallowInterceptTouchEvent控制父View是否拦截）。根据场景选择，如ViewPager嵌套RecyclerView用外部拦截。
- **评分关键词**：外部拦截、内部拦截、onInterceptTouchEvent、requestDisallowInterceptTouchEvent

---

### 2.2 布局

#### 问题21：Android常用布局有哪些？
- **难度系数**：0.2
- **追问深度**：基础概念
- **参考答案**：LinearLayout（线性）、RelativeLayout（相对）、FrameLayout（层叠）、ConstraintLayout（约束）、CoordinatorLayout（协调）。ConstraintLayout性能更好，是Google推荐布局。
- **评分关键词**：LinearLayout、RelativeLayout、ConstraintLayout、CoordinatorLayout

#### 问题22：ConstraintLayout有什么优势？
- **难度系数**：0.35
- **追问深度**：原理探究
- **参考答案**：1)减少布局层级（扁平化），提升性能；2)通过约束灵活定位；3)支持百分比、链条、引导线；4)可视化编辑更方便；5)减少嵌套带来的measure次数。
- **评分关键词**：扁平化、约束、百分比、链条、性能、measure

#### 问题23：如何优化布局层级？
- **难度系数**：0.55
- **追问深度**：场景应用
- **参考答案**：1)使用ConstraintLayout减少嵌套；2)使用merge标签合并布局；3)使用ViewStub延迟加载；4)移除无用父布局；5)使用include复用布局；6)避免过度绘制。
- **评分关键词**：ConstraintLayout、merge、ViewStub、include、过度绘制

---

### 2.3 RecyclerView

#### 问题24：RecyclerView相比ListView有什么优势？
- **难度系数**：0.3
- **追问深度**：基础概念
- **参考答案**：1)ViewHolder强制复用，ListView需手动实现；2)四级缓存机制（Scrap、Cache、ViewCacheExtension、RecycledPool），缓存更灵活；3)LayoutManager支持多种布局；4)ItemDecoration、ItemAnimator更灵活；5)局部刷新（notifyItemChanged）。
- **评分关键词**：ViewHolder、四级缓存、LayoutManager、局部刷新、ItemDecoration

#### 问题25：RecyclerView的缓存机制是怎样的？
- **难度系数**：0.6
- **追问深度**：原理探究
- **参考答案**：四级缓存：1)mAttachedScrap（当前屏幕内，可直接复用）；2)mCachedViews（刚移出屏幕，默认2个）；3)mViewCacheExtension（自定义缓存，需手动实现）；4)mRecycledViewPool（按ViewType缓存，可跨RecyclerView共享）。
- **评分关键词**：Scrap、CachedViews、ViewCacheExtension、RecycledViewPool、ViewType

#### 问题26：如何优化RecyclerView性能？
- **难度系数**：0.65
- **追问深度**：场景应用
- **参考答案**：1)setHasFixedSize(true)固定高度；2)使用DiffUtil局部更新；3)分页加载（Paging）；4)设置缓存大小（setItemViewCacheSize）；5)避免onBindViewHolder中复杂操作；6)图片加载使用合适尺寸；7)使用异步布局（AsyncLayoutInflater）。
- **评分关键词**：setHasFixedSize、DiffUtil、Paging、缓存大小、异步布局

---

### 2.4 动画

#### 问题27：属性动画和视图动画有什么区别？
- **难度系数**：0.4
- **追问深度**：原理探究
- **参考答案**：属性动画改变真实属性值，可作用于任意对象，支持插值器和估值器；视图动画仅改变视觉效果，不改变真实属性，执行后点击位置不变。属性动画更强大，推荐使用。
- **评分关键词**：属性动画、视图动画、真实属性、插值器、估值器

#### 问题28：Activity过渡动画如何实现？
- **难度系数**：0.5
- **追问深度**：场景应用
- **参考答案**：1)开启窗口动画支持（windowActivityTransitions）；2)设置共享元素（android:transitionName）；3)使用ActivityOptions.makeSceneTransitionAnimation启动；4)支持Explode、Slide、Fade等过渡效果。
- **评分关键词**：共享元素、transitionName、ActivityOptions、Explode、Slide

---

## 三、Android存储

### 3.1 数据存储方式

#### 问题29：Android数据存储方式有哪些？
- **难度系数**：0.25
- **追问深度**：基础概念
- **参考答案**：SharedPreferences（键值对）、内部存储（/data/data/package/files/）、外部存储（公有/私有目录）、SQLite数据库、Room（ORM）、网络存储。
- **评分关键词**：SharedPreferences、内部存储、外部存储、SQLite、Room

#### 问题30：SharedPreferences有什么缺点？如何优化？
- **难度系数**：0.45
- **追问深度**：原理探究
- **参考答案**：缺点：1)全量读写，数据大时性能差；2)commit同步阻塞主线程；3)apply异步但可能丢失数据；4)不支持多进程。优化：1)使用apply()替代commit()；2)批量修改使用Editor；3)考虑MMKV替代（mmap内存映射，性能高10倍）。
- **评分关键词**：全量读写、commit、apply、MMKV、mmap、多进程

#### 问题31：Android 10+分区存储有什么影响？
- **难度系数**：0.55
- **追问深度**：原理探究
- **参考答案**：分区存储限制应用只能访问自己的私有目录（Android/data/package/）和媒体文件（通过MediaStore）。不能直接访问其他应用的私有目录和外部存储根目录。需要访问其他文件时使用Storage Access Framework或申请MANAGE_EXTERNAL_STORAGE权限。
- **评分关键词**：分区存储、私有目录、MediaStore、SAF、权限

---

### 3.2 Room数据库

#### 问题32：Room的三个核心组件是什么？
- **难度系数**：0.3
- **追问深度**：基础概念
- **参考答案**：Entity（实体类，映射数据库表）、DAO（数据访问对象，定义增删改查方法）、Database（数据库持有者，定义实体和DAO）。
- **评分关键词**：Entity、DAO、Database、实体、数据访问

#### 问题33：Room相比直接使用SQLite有什么优势？
- **难度系数**：0.4
- **追问深度**：原理探究
- **参考答案**：1)编译时SQL检查，避免运行时错误；2)减少样板代码；3)支持LiveData/Flow自动观察数据变化；4)支持事务；5)支持数据库迁移；6)类型转换器支持复杂类型。
- **评分关键词**：编译时检查、LiveData、Flow、事务、迁移、类型转换器

---

## 四、Android网络

### 4.1 网络请求

#### 问题34：OkHttp有哪些优点？
- **难度系数**：0.35
- **追问深度**：基础概念
- **参考答案**：1)连接池复用TCP连接（HTTP/2多路复用）；2)拦截器机制（应用拦截器、网络拦截器）；3)自动GZIP压缩；4)响应缓存；5)失败重试和重定向；6)支持HTTPS和证书校验。
- **评分关键词**：连接池、拦截器、GZIP、缓存、HTTPS、多路复用

#### 问题35：Retrofit的工作原理是什么？
- **难度系数**：0.55
- **追问深度**：原理探究
- **参考答案**：Retrofit基于动态代理和注解。1)定义接口并用注解描述API；2)Retrofit.create()生成动态代理对象；3)调用方法时解析注解构建Request；4)通过CallAdapter适配返回值；5)Converter转换请求/响应数据；6)底层使用OkHttp执行请求。
- **评分关键词**：动态代理、注解、CallAdapter、Converter、OkHttp

#### 问题36：Retrofit的Converter和CallAdapter有什么区别？
- **难度系数**：0.6
- **追问深度**：原理探究
- **参考答案**：Converter负责数据转换（如GsonConverter将JSON转为对象，ScalarsConverter转为String）；CallAdapter负责适配返回值类型（如将Call<T>转为Observable<T>、LiveData<T>或suspend函数）。
- **评分关键词**：Converter、CallAdapter、数据转换、返回值适配、Gson

---

### 4.2 图片加载

#### 问题37：Glide的三级缓存是什么？
- **难度系数**：0.5
- **追问深度**：原理探究
- **参考答案**：1)活动资源（Active Resources）：弱引用缓存正在使用的图片；2)内存缓存（Memory Cache）：LruCache缓存最近使用；3)磁盘缓存（Disk Cache）：DiskLruCache持久化存储。读取顺序：活动资源→内存缓存→磁盘缓存→网络。
- **评分关键词**：活动资源、内存缓存、磁盘缓存、LruCache、弱引用

#### 问题38：如何优化Bitmap内存占用？
- **难度系数**：0.65
- **追问深度**：场景应用
- **参考答案**：1)使用inSampleSize采样加载合适尺寸；2)使用RGB_565格式（比ARGB_8888省一半内存）；3)复用Bitmap（inBitmap，Android 3.0+）；4)及时recycle()（Android 2.3前）；5)使用图片加载库（Glide自动优化）。
- **评分关键词**：inSampleSize、RGB_565、inBitmap、recycle、采样

---

## 五、Android多线程

### 5.1 线程基础

#### 问题39：什么是ANR？如何避免？
- **难度系数**：0.3
- **追问深度**：基础概念
- **参考答案**：ANR（Application Not Responding）是应用无响应。触发条件：主线程5秒内未响应输入事件、BroadcastReceiver 10秒内未完成、Service 20秒内未完成。避免方法：耗时操作放子线程，使用异步机制（Handler、AsyncTask、协程等）。
- **评分关键词**：ANR、主线程、5秒、10秒、20秒、子线程、异步

---

### 5.2 异步机制

#### 问题40：Handler机制的原理是什么？
- **难度系数**：0.55
- **追问深度**：原理探究
- **参考答案**：Handler、Looper、MessageQueue、Message四部分组成。Looper.prepare()创建Looper和MessageQueue；Handler发送Message到队列；Looper.loop()循环取出消息；Handler.handleMessage()处理。线程间通过Message传递数据。
- **评分关键词**：Handler、Looper、MessageQueue、Message、prepare、loop

#### 问题41：为什么子线程不能更新UI？
- **难度系数**：0.5
- **追问深度**：原理探究
- **参考答案**：Android UI组件非线程安全，多线程并发更新会导致界面混乱。主线程（UI线程）有Looper循环处理消息，子线程无Looper。通过Handler机制将更新操作发送到主线程执行，保证线程安全。
- **评分关键词**：线程安全、并发、Looper、Handler、主线程

#### 问题42：Handler可能导致内存泄漏吗？如何解决？
- **难度系数**：0.6
- **追问深度**：场景应用
- **参考答案**：会。非静态内部类Handler持有外部Activity引用，延迟消息未处理时Activity无法回收。解决：1)使用静态内部类+弱引用；2)Activity销毁时移除消息（removeCallbacksAndMessages）；3)使用Lifecycle组件自动管理。
- **评分关键词**：内存泄漏、静态内部类、弱引用、removeCallbacks、Lifecycle

#### 问题43：AsyncTask有什么问题？推荐用什么替代？
- **难度系数**：0.5
- **追问深度**：原理探究
- **参考答案**：问题：1)默认串行执行，并发需设置THREAD_POOL_EXECUTOR；2)API 11+改为串行，可能导致任务排队；3)内存泄漏风险；4)已弃用（API 30）。替代：HandlerThread、ThreadPoolExecutor、Kotlin协程、RxJava。
- **评分关键词**：串行执行、内存泄漏、已弃用、协程、RxJava

---

### 5.3 Kotlin协程

#### 问题44：Kotlin协程是什么？有什么优势？
- **难度系数**：0.4
- **追问深度**：原理探究
- **参考答案**：协程是轻量级线程，由Kotlin管理调度。优势：1)轻量，一个线程可运行多个协程；2)挂起函数（suspend）非阻塞；3)代码简洁，像同步写异步；4)结构化并发，自动取消子协程；5)与LiveData、Flow集成好。
- **评分关键词**：轻量级、挂起函数、非阻塞、结构化并发、Flow

#### 问题45：launch和async有什么区别？
- **难度系数**：0.45
- **追问深度**：原理探究
- **参考答案**：launch启动新协程，返回Job（无返回值）；async启动新协程，返回Deferred（有返回值，通过await获取）。async用于并发执行多个任务并等待结果，launch用于不关心返回值的后台任务。
- **评分关键词**：launch、async、Job、Deferred、await、并发

#### 问题46：Dispatchers.Main、IO、Default有什么区别？
- **难度系数**：0.5
- **追问深度**：原理探究
- **参考答案**：Dispatchers.Main：主线程，更新UI；Dispatchers.IO：IO线程池（64线程），网络/数据库操作；Dispatchers.Default：CPU密集型任务（线程数=CPU核心数），计算/排序。根据任务类型选择，自动切换。
- **评分关键词**：Main、IO、Default、主线程、线程池、CPU密集

#### 问题47：高并发场景下你会怎么选择线程模型？
- **难度系数**：0.75
- **追问深度**：场景应用
- **参考答案**：IO密集型（网络请求）用Dispatchers.IO；CPU密集型（图片处理）用Dispatchers.Default；需要顺序执行用单线程上下文（newSingleThreadContext）；大量并发任务用自定义线程池限制并发数。Kotlin协程的挂起机制比回调更节省线程资源，适合高并发。
- **评分关键词**：Dispatchers.IO、Dispatchers.Default、单线程、自定义线程池、挂起

---

## 六、Android架构

### 6.1 MVP与MVVM

#### 问题48：MVP和MVVM有什么区别？
- **难度系数**：0.45
- **追问深度**：原理探究
- **参考答案**：MVP：Presenter持有View接口，通过接口更新UI，View和Model完全隔离，接口多代码冗余。MVVM：ViewModel不持有View，通过DataBinding或LiveData数据驱动UI，更简洁，是Google推荐架构。
- **评分关键词**：Presenter、ViewModel、接口、数据驱动、DataBinding、LiveData

#### 问题49：MVVM中ViewModel如何与View通信？
- **难度系数**：0.5
- **追问深度**：原理探究
- **参考答案**：1)LiveData：ViewModel持有LiveData，View观察数据变化自动更新；2)DataBinding：布局中绑定ViewModel数据，双向绑定；3)StateFlow/SharedFlow：Kotlin协程的响应式流。ViewModel不直接操作View，通过数据驱动。
- **评分关键词**：LiveData、DataBinding、StateFlow、观察、数据驱动

---

### 6.2 Jetpack组件

#### 问题50：ViewModel有什么特点？
- **难度系数**：0.4
- **追问深度**：原理探究
- **参考答案**：1)生命周期感知，配置变更（旋转屏幕）后数据保留；2)不持有View引用，避免内存泄漏；3)与Activity/Fragment生命周期绑定；4)适合存储UI相关数据；5)通过ViewModelProvider.Factory创建。
- **评分关键词**：生命周期感知、配置变更、数据保留、不持有View

#### 问题51：LiveData和Flow有什么区别？
- **难度系数**：0.55
- **追问深度**：原理探究
- **参考答案**：LiveData：Android专属，生命周期感知，自动管理订阅，主线程更新；Flow：Kotlin标准库，响应式流，需手动管理生命周期，支持各种操作符（map、filter等），可在任意协程上下文发射数据。新推荐Flow替代LiveData。
- **评分关键词**：生命周期感知、响应式流、操作符、协程、主线程

#### 问题52：WorkManager的作用是什么？
- **难度系数**：0.45
- **追问深度**：基础概念
- **参考答案**：WorkManager用于调度可延迟的后台任务，保证任务执行（即使应用退出或重启）。支持约束条件（网络、电量、存储等）、链式任务、周期性任务。适合上传日志、同步数据等不紧急任务。
- **评分关键词**：后台任务、保证执行、约束条件、链式任务、周期性

---

### 6.3 依赖注入

#### 问题53：Hilt和Dagger有什么区别？
- **难度系数**：0.5
- **追问深度**：原理探究
- **参考答案**：Hilt是基于Dagger的依赖注入框架，简化了Dagger的使用。Hilt提供预定义的组件（Application、Activity、Fragment等），自动生成组件代码，减少样板代码。Dagger更灵活但配置复杂，Hilt更适合Android开发。
- **评分关键词**：Hilt、Dagger、预定义组件、自动生成、简化

---

## 七、Android性能优化

### 7.1 内存优化

#### 问题54：内存泄漏的常见原因有哪些？
- **难度系数**：0.45
- **追问深度**：原理探究
- **参考答案**：1)静态变量持有Activity；2)匿名内部类持有外部类引用；3)未取消注册监听器/广播；4)Handler延迟消息持有Activity；5)资源未关闭（Cursor、File）；6)单例持有Context；7)WebView未正确销毁。
- **评分关键词**：静态变量、匿名内部类、监听器、Handler、Cursor、单例、WebView

#### 问题55：如何检测内存泄漏？
- **难度系数**：0.5
- **追问深度**：场景应用
- **参考答案**：1)LeakCanary：自动检测并通知；2)Android Studio Profiler：查看内存分配和堆转储；3)MAT分析hprof文件，查找GC Roots；4)adb shell dumpsys meminfo查看内存占用。
- **评分关键词**：LeakCanary、Profiler、MAT、hprof、GC Roots

#### 问题56：什么是内存抖动？如何解决？
- **难度系数**：0.55
- **追问深度**：场景应用
- **参考答案**：内存抖动是短时间内大量对象创建和销毁，导致GC频繁。解决：1)避免onDraw中创建对象；2)使用对象池复用对象；3)使用StringBuilder替代String拼接；4)减少临时对象创建。
- **评分关键词**：GC频繁、onDraw、对象池、StringBuilder、临时对象

---

### 7.2 UI优化

#### 问题57：什么是过度绘制？如何避免？
- **难度系数**：0.5
- **追问深度**：场景应用
- **参考答案**：过度绘制是同一像素被绘制多次。避免：1)移除不必要的背景；2)使用clipRect减少绘制区域；3)使用ViewStub延迟加载；4)优化布局层级；5)使用开发者选项中的"调试GPU过度绘制"检测。
- **评分关键词**：背景、clipRect、ViewStub、布局层级、GPU过度绘制

#### 问题58：如何检测和解决卡顿？
- **难度系数**：0.65
- **追问深度**：场景应用
- **参考答案**：检测：1)Systrace分析UI线程；2)Choreographer检测掉帧；3)BlockCanary检测主线程阻塞。解决：1)避免主线程耗时操作；2)懒加载和分页加载；3)使用RecyclerView替代ListView；4)优化布局层级；5)异步初始化。
- **评分关键词**：Systrace、Choreographer、BlockCanary、主线程、懒加载

---

### 7.3 启动优化

#### 问题59：冷启动和热启动有什么区别？
- **难度系数**：0.35
- **追问深度**：基础概念
- **参考答案**：冷启动：应用首次启动，创建进程，加载Application和Activity，时间较长。热启动：应用从后台回到前台，进程存在，只需恢复Activity，时间较短。
- **评分关键词**：冷启动、热启动、创建进程、Application、后台

#### 问题60：如何优化应用冷启动速度？
- **难度系数**：0.7
- **追问深度**：场景应用
- **参考答案**：1)延迟初始化（懒加载）；2)异步初始化（子线程）；3)优化Application.onCreate()；4)使用ContentProvider延迟初始化（Startup库）；5)使用SplashTheme避免白屏；6)减少布局层级；7)预加载常用数据。
- **评分关键词**：延迟初始化、异步初始化、Startup库、SplashTheme、白屏

---

### 7.4 APK瘦身

#### 问题61：APK瘦身有哪些方法？
- **难度系数**：0.55
- **追问深度**：场景应用
- **参考答案**：1)资源混淆（AndResGuard）；2)图片压缩（WebP、TinyPNG）；3)移除无用资源（lint）；4)代码混淆（ProGuard/R8）；5)只保留必要ABI（so库）；6)使用Android App Bundle动态交付；7)资源动态下发（插件化）。
- **评分关键词**：资源混淆、WebP、ProGuard、ABI、App Bundle、插件化

---

## 八、Android安全

#### 问题62：如何安全存储敏感数据？
- **难度系数**：0.6
- **追问深度**：场景应用
- **参考答案**：1)使用Android Keystore系统生成和存储密钥；2)敏感数据加密存储（AES加密）；3)密钥不硬编码在代码中；4)SharedPreferences使用MODE_PRIVATE；5)考虑使用SQLCipher加密数据库。
- **评分关键词**：Keystore、AES加密、密钥、MODE_PRIVATE、SQLCipher

#### 问题63：HTTPS通信如何防止中间人攻击？
- **难度系数**：0.65
- **追问深度**：场景应用
- **参考答案**：1)证书绑定（Certificate Pinning），只信任指定证书；2)校验服务器证书链；3)不使用ALLOW_ALL_HOSTNAME_VERIFIER；4)OkHttp配置自定义TrustManager校验证书；5)使用公钥固定（Public Key Pinning）。
- **评分关键词**：证书绑定、证书链、TrustManager、公钥固定、校验

---

## 九、Android系统机制

### 9.1 Binder机制

#### 问题64：Binder机制有什么特点？
- **难度系数**：0.6
- **追问深度**：原理探究
- **参考答案**：1)基于C/S架构；2)一次内存拷贝（优于管道、Socket的两次拷贝）；3)支持实名（ServiceManager注册）和匿名Binder；4)安全性好（基于UID/PID校验）；5)是Android IPC的主要方式。
- **评分关键词**：C/S架构、一次拷贝、实名Binder、匿名Binder、IPC

#### 问题65：为什么Android选择Binder作为IPC机制？
- **难度系数**：0.75
- **追问深度**：极限深挖
- **参考答案**：1)性能：Binder只需一次内存拷贝（管道/Socket需两次），通过mmap实现内核空间和接收方用户空间映射同一块物理内存；2)安全：基于UID/PID识别身份，内核层校验；3)易用：面向对象的调用方式，像本地方法调用；4)稳定性：C/S架构，服务端崩溃不影响客户端。Linux传统IPC（管道、消息队列、共享内存、Socket）在性能、安全、易用性方面不如Binder。
- **评分关键词**：mmap、一次拷贝、UID/PID、面向对象、C/S架构

---

### 9.2 AMS与WMS

#### 问题66：AMS的作用是什么？
- **难度系数**：0.5
- **追问深度**：原理探究
- **参考答案**：AMS（ActivityManagerService）是Android核心服务，管理Activity、Service、BroadcastReceiver生命周期，管理进程和任务栈，调度组件启动，管理应用进程（oom_adj优先级）。
- **评分关键词**：生命周期、任务栈、进程管理、oom_adj、调度

#### 问题67：WMS的作用是什么？
- **难度系数**：0.5
- **追问深度**：原理探究
- **参考答案**：WMS（WindowManagerService）管理窗口的添加、删除、更新，计算窗口大小和位置，管理窗口层级（Z-order），处理窗口动画，分发输入事件到窗口。
- **评分关键词**：窗口管理、Z-order、动画、输入事件、层级

---

### 9.3 消息机制

#### 问题68：MessageQueue的数据结构是什么？
- **难度系数**：0.65
- **追问深度**：极限深挖
- **参考答案**：MessageQueue使用单链表结构，按when（消息触发时间）排序。新消息插入时按时间顺序插入合适位置。使用nativePollOnce在Native层阻塞等待，超时或有新消息时唤醒。
- **评分关键词**：单链表、when、时间排序、nativePollOnce、阻塞唤醒

#### 问题69：为什么主线程的Looper不会阻塞UI？
- **难度系数**：0.7
- **追问深度**：极限深挖
- **参考答案**：Looper.loop()确实是死循环，但阻塞的是Native层的epoll_wait，不会消耗CPU。当有消息时（用户操作、屏幕刷新等）被唤醒处理，处理完后继续阻塞等待。Android基于事件驱动，没有消息时主线程休眠，有事件时唤醒处理，所以不会ANR。ANR是因为处理消息耗时过长，不是循环本身的问题。
- **评分关键词**：epoll_wait、事件驱动、阻塞、唤醒、ANR、耗时

---

### 9.4 屏幕刷新机制

#### 问题70：Choreographer的作用是什么？
- **难度系数**：0.6
- **追问深度**：原理探究
- **参考答案**：Choreographer协调动画、输入、绘制的节奏。接收VSync信号（16.6ms一次，60fps），在VSync到来时触发回调（doFrame），执行输入处理、动画、绘制等操作，保证UI刷新与屏幕刷新同步，避免画面撕裂。
- **评分关键词**：VSync、doFrame、动画、绘制、同步、画面撕裂

---

## 十、Android新技术

### 10.1 Jetpack Compose

#### 问题71：Jetpack Compose有什么特点？
- **难度系数**：0.45
- **追问深度**：基础概念
- **参考答案**：1)声明式UI，描述UI应该是什么样而非如何创建；2)Kotlin DSL，代码简洁；3)实时预览；4)状态驱动UI，自动重组；5)无需XML布局；6)与现有View系统互操作。
- **评分关键词**：声明式、DSL、实时预览、状态驱动、重组、互操作

#### 问题72：Compose的重组（Recomposition）是什么？
- **难度系数**：0.6
- **追问深度**：原理探究
- **参考答案**：重组是Compose根据状态变化重新执行Composable函数更新UI的过程。Compose会智能跳过未变化的Composable，只重组受影响的部分。使用remember缓存状态，使用derivedStateOf派生状态减少重组次数。
- **评分关键词**：重组、状态变化、智能跳过、remember、derivedStateOf

---

### 10.2 Kotlin

#### 问题73：Kotlin的Flow和RxJava有什么区别？
- **难度系数**：0.65
- **追问深度**：原理探究
- **参考答案**：Flow：Kotlin标准库，协程支持，冷流（默认），结构化并发，简洁；RxJava：第三方库，多语言支持，热流冷流都有，功能丰富但学习曲线陡。Flow更适合Kotlin项目，与协程集成更好。
- **评分关键词**：标准库、协程、冷流、热流、结构化并发

#### 问题74：StateFlow和SharedFlow有什么区别？
- **难度系数**：0.6
- **追问深度**：原理探究
- **参考答案**：StateFlow：热流，必须有初始值，只保留最新值，适合状态管理（替代LiveData）；SharedFlow：热流，可配置缓存数量（replay），无初始值，适合事件分发。两者都是协程的响应式流。
- **评分关键词**：StateFlow、SharedFlow、热流、初始值、replay、状态管理

---

## 十一、系统设计与架构

#### 问题75：如何设计一个图片加载框架？
- **难度系数**：0.8
- **追问深度**：场景应用
- **参考答案**：1)内存缓存：LruCache；2)磁盘缓存：DiskLruCache；3)网络下载：OkHttp；4)图片解码：BitmapFactory，支持inSampleSize采样；5)线程池：管理下载和解码任务；6)图片变换：缩放、圆角等；7)生命周期管理：与Activity/Fragment绑定自动取消。参考Glide架构。
- **评分关键词**：LruCache、DiskLruCache、OkHttp、inSampleSize、线程池、生命周期

#### 问题76：如何设计一个网络请求框架？
- **难度系数**：0.8
- **追问深度**：场景应用
- **参考答案**：1)底层：OkHttp执行请求；2)API定义：注解描述（@GET、@POST等）；3)动态代理生成实现；4)数据转换：Converter（JSON/XML转对象）；5)适配器：CallAdapter（适配协程/RxJava）；6)拦截器：日志、缓存、重试；7)生命周期管理：自动取消请求。
- **评分关键词**：OkHttp、注解、动态代理、Converter、CallAdapter、拦截器

#### 问题77：如何设计一个组件化架构？
- **难度系数**：0.85
- **追问深度**：场景应用
- **参考答案**：1)模块划分：业务组件（独立module）、基础组件（公共库）；2)模块间通信：ARouter路由（URL跳转）、接口下沉（base模块定义接口）；3)依赖管理：每个组件可独立编译运行；4)资源隔离：资源名前缀避免冲突；5)生命周期管理：组件独立初始化（APT生成代码）。
- **评分关键词**：业务组件、基础组件、ARouter、接口下沉、资源隔离、APT

#### 问题78：如何设计一个热修复方案？
- **难度系数**：0.9
- **追问深度**：极限深挖
- **参考答案**：1)类替换：Tinker（Dex插桩，全量替换，需重启）；2)类插桩：Robust（AOP插桩，实时生效，方法级修复）；3)资源替换：AssetManager反射替换资源路径；4)So替换：System.load动态加载。方案选择：Tinker稳定但需重启，Robust实时但侵入性强。需考虑：补丁下发、签名校验、版本管理、回滚机制。
- **评分关键词**：Tinker、Robust、Dex插桩、AOP、AssetManager、签名校验

#### 问题79：如何设计一个插件化框架？
- **难度系数**：0.95
- **追问深度**：极限深挖
- **参考答案**：1)Dex加载：PathClassLoader/DexClassLoader加载插件Dex；2)资源加载：反射创建AssetManager，addAssetPath加载插件资源；3)四大组件：占坑（预注册壳组件）+ Hook（Instrumentation/AMS代理替换Intent）；4)生命周期：代理分发到插件组件；5)SO加载：自定义NativeLibraryPathElement。核心技术：Hook（反射+动态代理）、占坑、ClassLoader隔离。
- **评分关键词**：DexClassLoader、AssetManager、占坑、Hook、Instrumentation、动态代理

#### 问题80：如何优化RecyclerView加载大量图片时的性能？
- **难度系数**：0.75
- **追问深度**：场景应用
- **参考答案**：1)图片尺寸适配：根据ImageView大小加载合适尺寸图片；2)滑动暂停加载：onScrollStateChanged中判断滑动状态，滑动时暂停加载；3)预加载：提前加载即将可见的Item图片；4)缓存优化：合理设置内存和磁盘缓存大小；5)图片复用：ViewHolder复用，图片加载库自动处理；6)降低图片质量：RGB_565格式。
- **评分关键词**：尺寸适配、滑动暂停、预加载、缓存、RGB_565、ViewHolder
