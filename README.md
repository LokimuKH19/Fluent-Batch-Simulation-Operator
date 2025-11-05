# Fluent-Batch-Simulation-Operator / FLuent 批量仿真器
A Fluent batch simulator (2020R2)

> 貌似只对Fluent 2020 R2 有用

> Due to I am very lazy therefore I am not willing to translate the comments and the documentaries into English in this repo. For the code is very old (earlier in 2024) If someone is extremely spare, just do this for me.

> There's only one program file: main.py. Including all of the functions of this tool.


## 用法
- 第零步：开着Fluent jou文件录制功能手动做一遍输入输出，看看生成的jou文件是什么格式，从而针对性地修改此程序
- 第一步：先用一组输入参数生成一个settings文件，打开settings文件找到以(rbp/scenarios/save-load)和(rbp/scenario)开头的行，确定各输入变量和中间变量的顺序（旧功能，好像需要一个什么rpb插件，可能已报废）
- 第二步：在本软件中输入各输入变量的上下限，希望生成的参数组个数以及对每组参数迭代计算的次数，并给出中间变量的一组取值(删除变量需双击变量名)
- 第三步：生成excel文件，可查看并手动调节输入变量值
- 第四步：在本软件中生成字符串，替换原有的以(rbp/scenarios/save-load)和(rbp/scenarios)开头的行（旧功能，好像需要一个什么rpb插件，可能已报废）
- 第五步（新功能）：请确保在完成了签署步骤后不关闭软件，点击生成jou文件可在同样目录下生成对应的jou文件，用fluent生成可读的模型训练集（不要关闭软件）和按曲面生成的几何文件
- 第六步（新功能）：点击压缩训练集，得到压缩后的traindata文件夹

## 说明
由于实在是找不到Ansys Deployer的破解方法所以用以上方式部署模型是没指望了，除非氪金

点击生成jou文件按钮生成这个文件，在fluent中打开设置好的cas文件，然后在fluent中Read->Journal启动生成训练集，之后建立降阶模型，这个模型相比于Ansys Twins完全开源(Why I explored Ansys Twins 1 year ago??? Doesn't make sense???)且可以随便导出

生成的训练集模型在cas文件目录下的traindata_csv文件夹中，然后你用现在有的各种数据驱动算法随便搞就可以出论文了

至于定义了中间变量的情况该咋搞我没打算研究，因为完全可以在各输入框中写表达式，NamedExpressions中只用写输入变量就可以了
