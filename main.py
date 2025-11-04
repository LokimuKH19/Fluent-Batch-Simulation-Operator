# fluent仿真rbp扩展生成仿真参数的插件
import tkinter as tk
from tkinter import scrolledtext
from tkinter import messagebox
from tkinter import simpledialog
from tkinter import filedialog
import pandas as pd
import numpy as np
import pyperclip
import os
# 仅针对Fluent 2020R2有效，别的版本不清楚


# 拉丁超立方采样，但实际发现160个工况参数太少，研究过程中不便于比对训练集和模型，在生成的excel中手动改成了更容易被记住规律的均匀采样
def generate_latin_hypercube(variables_map, num_samples):
    num_variables = len(variables_map)

    latin_hypercube = np.zeros((num_samples, num_variables))
    step_size = 1 / num_samples

    # 生成初始拉丁超立方采样矩阵
    for i in range(num_variables):
        column_values = np.arange(0, 1, step_size)
        np.random.shuffle(column_values)
        latin_hypercube[:, i] = column_values

    # 根据上下限调整采样值
    for i, (var, limits) in enumerate(variables_map.items()):
        lower_limit, upper_limit = limits['lower_limit'], limits['upper_limit']
        latin_hypercube[:, i] = latin_hypercube[:, i] * (upper_limit - lower_limit) + lower_limit

        # 通过随机打乱来确保采样值分布均匀
        np.random.shuffle(latin_hypercube[:, i])

        # 过滤掉位于上下限之外的采样值
        latin_hypercube[:, i] = np.clip(latin_hypercube[:, i], lower_limit, upper_limit)

    return latin_hypercube


# 界面
class RBPstringGUI:
    def __init__(self):
        self.window = tk.Tk()
        self.window.title("Fluent批量仿真器")

        self.input_variables_frame = tk.LabelFrame(self.window, text="输入变量")
        self.input_variables_frame.grid(row=0, column=0, padx=10, pady=10)

        self.input_key_label = tk.Label(self.input_variables_frame, text="变量名:")
        self.input_key_label.grid(row=0, column=0, sticky=tk.W)
        self.input_key_entry = tk.Entry(self.input_variables_frame)
        self.input_key_entry.grid(row=0, column=1, padx=5, pady=5)

        self.input_lower_limit_label = tk.Label(self.input_variables_frame, text="下限:")
        self.input_lower_limit_label.grid(row=1, column=0, sticky=tk.W)
        self.input_lower_limit_entry = tk.Entry(self.input_variables_frame)
        self.input_lower_limit_entry.grid(row=1, column=1, padx=5, pady=5)

        self.input_upper_limit_label = tk.Label(self.input_variables_frame, text="上限:")
        self.input_upper_limit_label.grid(row=2, column=0, sticky=tk.W)
        self.input_upper_limit_entry = tk.Entry(self.input_variables_frame)
        self.input_upper_limit_entry.grid(row=2, column=1, padx=5, pady=5)

        self.input_unit_label = tk.Label(self.input_variables_frame, text="单位:")
        self.input_unit_label.grid(row=3, column=0, sticky=tk.W)
        self.input_unit_entry = tk.Entry(self.input_variables_frame)
        self.input_unit_entry.grid(row=3, column=1, padx=5, pady=5)

        self.add_input_variable_button = tk.Button(self.input_variables_frame, text="添加变量",
                                                   command=self.add_input_variable)
        self.add_input_variable_button.grid(row=4, column=0, columnspan=2, padx=5, pady=10)

        self.delete_input_variable_button = tk.Button(self.input_variables_frame, text="删除变量",
                                                      command=self.delete_input_variable)
        self.delete_input_variable_button.grid(row=5, column=0, columnspan=2, padx=5, pady=5)

        self.input_variables_listbox = scrolledtext.ScrolledText(self.input_variables_frame, width=35, height=10)
        self.input_variables_listbox.grid(row=6, column=0, columnspan=2, padx=5, pady=5)
        self.input_variables_listbox.configure(state='disabled')

        self.intermediate_variables_frame = tk.LabelFrame(self.window, text="中间变量")
        self.intermediate_variables_frame.grid(row=0, column=1, padx=10, pady=10)

        self.intermediate_key_label = tk.Label(self.intermediate_variables_frame, text="变量名:")
        self.intermediate_key_label.grid(row=0, column=0, sticky=tk.W)
        self.intermediate_key_entry = tk.Entry(self.intermediate_variables_frame)
        self.intermediate_key_entry.grid(row=0, column=1, padx=5, pady=5)

        self.intermediate_value_label = tk.Label(self.intermediate_variables_frame, text="参考值:")
        self.intermediate_value_label.grid(row=1, column=0, sticky=tk.W)
        self.intermediate_value_entry = tk.Entry(self.intermediate_variables_frame)
        self.intermediate_value_entry.grid(row=1, column=1, padx=5, pady=5)

        self.add_intermediate_variable_button = tk.Button(self.intermediate_variables_frame, text="添加变量",
                                                          command=self.add_intermediate_variable)
        self.add_intermediate_variable_button.grid(row=2, column=0, columnspan=2, padx=5, pady=10)

        self.delete_intermediate_variable_button = tk.Button(self.intermediate_variables_frame, text="删除变量",
                                                             command=self.delete_intermediate_variable)
        self.delete_intermediate_variable_button.grid(row=3, column=0, columnspan=2, padx=5, pady=5)

        self.intermediate_variables_listbox = scrolledtext.ScrolledText(self.intermediate_variables_frame,
                                                                        width=35, height=10)
        self.intermediate_variables_listbox.grid(row=4, column=0, columnspan=2, padx=5, pady=5)
        self.intermediate_variables_listbox.configure(state='disabled')

        self.input_variables_map = {}
        self.intermediate_variables_map = {}

        self.run_settings_frame = tk.LabelFrame(self.window, text="运行设置")
        self.run_settings_frame.grid(row=1, column=0, padx=10, pady=10)

        self.iteration_times_label = tk.Label(self.run_settings_frame, text="迭代次数:")
        self.iteration_times_label.grid(row=0, column=0, sticky=tk.W)
        self.iteration_times_entry = tk.Entry(self.run_settings_frame)
        self.iteration_times_entry.grid(row=0, column=1, padx=5, pady=5)

        self.scenario_numbers_label = tk.Label(self.run_settings_frame, text="样本数:")
        self.scenario_numbers_label.grid(row=1, column=0, sticky=tk.W)
        self.scenario_numbers_entry = tk.Entry(self.run_settings_frame)
        self.scenario_numbers_entry.grid(row=1, column=1, padx=5, pady=5)

        self.compressed_sample_number_label = tk.Label(self.run_settings_frame, text="压缩训练集采样点数(建议1000~5000)：")
        self.compressed_sample_number_label.grid(row=2, column=0, sticky=tk.W)
        self.compressed_sample_number_entry = tk.Entry(self.run_settings_frame)
        self.compressed_sample_number_entry.grid(row=2, column=1, padx=5, pady=5)

        self.manipulate_frame = tk.LabelFrame(self.window, text="操作")
        self.manipulate_frame.grid(row=1, column=1, padx=10, pady=10)
        self.write_excel_button = tk.Button(self.manipulate_frame, text="写入excel", command=self.write_excel)
        self.write_excel_button.grid(row=0, column=0, padx=5, pady=5)
        self.summon_string_button = tk.Button(self.manipulate_frame, text="生成字符串", command=self.summon_string)
        self.summon_string_button.grid(row=0, column=1, padx=5, pady=5)
        self.copy_save_load_button = tk.Button(self.manipulate_frame, text="复制左侧", command=self.copy_save_load)
        self.copy_save_load_button.grid(row=1, column=0, padx=5, pady=5)
        self.copy_scenario_button = tk.Button(self.manipulate_frame, text="复制右侧", command=self.copy_scenario)
        self.copy_scenario_button.grid(row=1, column=1, padx=5, pady=5)
        self.summon_jou_code_button = tk.Button(self.manipulate_frame, text="生成jou文件", command=self.summon_jou_code)
        self.summon_jou_code_button.grid(row=0, column=2, padx=5, pady=5)
        self.compress_train_data_button = tk.Button(self.manipulate_frame, text="压缩训练集",
                                                    command=self.compress_train_data)
        self.compress_train_data_button.grid(row=1, column=2, padx=5, pady=5)
        self.save_load_frame = tk.LabelFrame(self.window, text="(rbp/scenarios/save-load)")
        self.save_load_frame.grid(row=2, column=0, padx=10, pady=20)
        self.summon_surface_code_button = tk.Button(self.manipulate_frame, text="导出表面",
                                                    command=self.summon_surface_code)
        self.summon_surface_code_button.grid(row=0, column=3, padx=5, pady=5)

        self.save_load_textbox = tk.Text(self.save_load_frame, width=35, height=10)
        self.save_load_textbox.grid(row=0, column=0, padx=5, pady=5, columnspan=1)
        self.save_load_textbox.configure(state="disabled")

        self.scenarios_frame = tk.LabelFrame(self.window, text="(rbp/scenarios)")
        self.scenarios_frame.grid(row=2, column=1, padx=10, pady=20)

        self.scenarios_textbox = tk.Text(self.scenarios_frame, width=35, height=10)
        self.scenarios_textbox.grid(row=0, column=0, padx=5, pady=5, columnspan=1)
        self.scenarios_textbox.configure(state="disabled")

        self.excel_path = "./parameters.xlsx"

    def add_input_variable(self):
        key = self.input_key_entry.get()
        lower_limit = float(self.input_lower_limit_entry.get())
        upper_limit = float(self.input_upper_limit_entry.get())
        unit = self.input_unit_entry.get()

        if key:
            self.input_variables_map[key] = {'lower_limit': lower_limit, 'upper_limit': upper_limit, 'unit': unit}
            self.update_input_variables_listbox()
            if lower_limit >= upper_limit:
                messagebox.showerror("Error", "上限应当大于下限")
                return
        else:
            messagebox.showerror("Error", "请先输入变量名")

    def add_intermediate_variable(self):
        key = self.intermediate_key_entry.get()
        value = float(self.intermediate_value_entry.get())

        if key:
            self.intermediate_variables_map[key] = {'value': value}
            self.update_intermediate_variables_listbox()
        else:
            messagebox.showerror("Error", "请先输入变量名")

    def delete_input_variable(self):
        selected_variable = self.input_variables_listbox.get(tk.SEL_FIRST, tk.SEL_LAST)
        if selected_variable:
            variable_name = selected_variable.split(' ')[0]
            del self.input_variables_map[variable_name]
            self.update_input_variables_listbox()

    def delete_intermediate_variable(self):
        selected_variable = self.intermediate_variables_listbox.get(tk.SEL_FIRST, tk.SEL_LAST)
        if selected_variable:
            variable_name = selected_variable.split(' ')[0]
            del self.intermediate_variables_map[variable_name]
            self.update_intermediate_variables_listbox()

    def update_input_variables_listbox(self):
        self.input_variables_listbox.configure(state='normal')
        self.input_variables_listbox.delete('1.0', tk.END)
        for key, value in self.input_variables_map.items():
            self.input_variables_listbox.insert(tk.END, "{} [{}, {}, {}]\n".format(
                key, value['lower_limit'], value['upper_limit'], value['unit'])
            )
        self.input_variables_listbox.configure(state='disabled')

    def update_intermediate_variables_listbox(self):
        self.intermediate_variables_listbox.configure(state='normal')
        self.intermediate_variables_listbox.delete('1.0', tk.END)
        for key, value in self.intermediate_variables_map.items():
            self.intermediate_variables_listbox.insert(tk.END, "{} [{}]\n".format(key, value['value']))
        self.intermediate_variables_listbox.configure(state='disabled')

    def write_excel(self):
        # 拉丁超立方采样写入
        # 检查是否有输入变量
        if not self.input_variables_map:
            messagebox.showerror("Error", "请添加输入变量")
            return

        # 创建DataFrame来存储数据
        variables = list(self.input_variables_map.keys()) + list(self.intermediate_variables_map.keys())
        df = pd.DataFrame(columns=variables)

        # 生成拉丁超立方采样数据
        num_samples = int(self.scenario_numbers_entry.get()) if self.scenario_numbers_entry.get().isdigit() else 0
        latin_hypercube = generate_latin_hypercube(self.input_variables_map, num_samples)

        # 填充输入变量数据
        for i, var in enumerate(self.input_variables_map):
            df[var] = latin_hypercube[:, i]

        # 填充中间变量数据
        for var, value in self.intermediate_variables_map.items():
            df[var] = value['value']

        # 写入Excel文件
        filename = self.excel_path
        df.to_excel(filename, index=False)
        messagebox.showinfo("Success", "参数数据已成功写入Excel文件: {}".format(filename))

    def summon_string(self):
        # 读取 Excel 文件
        df = pd.read_excel(self.excel_path)
        heads = df.columns
        values = df.values
        iteration_times = self.iteration_times_entry.get()
        if not iteration_times:
            messagebox.showerror("Error", "请输入迭代次数！")
            return
        # 构建字符串
        result_left = "(rbp/scenarios/save-load ("
        result_right = "(rbp/scenarios/ ("
        for i in range(len(values)):
            parameters = ""
            for j in range(len(heads)):
                if j != len(heads) - 1:
                    parameters += f'''("{heads[j]}" "constant" ({values[i][j]})) '''
                else:
                    parameters += f'''("{heads[j]}" "constant" ({values[i][j]}))'''
            if i != len(values) - 1:
                result_left += f'''("scenario{i + 1}" 0 {iteration_times} ({parameters})) '''
                result_right += f'''("scenario{i + 1}" 0 {iteration_times} ({parameters})) '''
            else:
                result_left += f'''("scenario{i + 1}" 0 {iteration_times} ({parameters}))'''
                result_right += f'''("scenario{i + 1}" 0 {iteration_times} ({parameters}))'''
        result_left += f'''))'''
        result_right += f'''))'''
        # 将结果显示在文本框中
        self.save_load_textbox.delete('1.0', 'end')
        self.save_load_textbox.configure(state="normal")
        self.save_load_textbox.insert('end', result_left)
        self.save_load_textbox.configure(state="disabled")

        self.scenarios_textbox.delete('1.0', 'end')
        self.scenarios_textbox.configure(state="normal")
        self.scenarios_textbox.insert('end', result_right)
        self.scenarios_textbox.configure(state="disabled")

    def copy_save_load(self):
        pyperclip.copy(self.save_load_textbox.get("1.0", tk.END))

    def copy_scenario(self):
        pyperclip.copy(self.scenarios_textbox.get("1.0", tk.END))

    def summon_jou_code(self):
        # 读取 Excel 文件
        df = pd.read_excel(self.excel_path)
        heads = df.columns
        values = df.values
        iteration_times = self.iteration_times_entry.get()
        if not iteration_times:
            messagebox.showerror("Error", "请输入迭代次数！")
            return
        for key in heads:
            if key not in self.input_variables_map.keys():
                messagebox.showerror("Error", "请先保证输入变量信息和Excel一致")
                return
        # 询问用户输出变量
        user_input = simpledialog.askstring("输入场变量，各变量以空格隔开", "例:x-velocity y-velocity z-velocity absolute-pressure")
        # 询问用户需要求解的平面
        surface_input = simpledialog.askstring("输入需要求解的平面，空间求解可跳过", "以空格隔开")
        # 询问用户输出的监测变量
        iswai = simpledialog.askstring("导出外特性？", "输入y导出，否则默认不导出")
        # 输出结果TUI代码
        result = ""
        for i in range(len(values)):
            result += "/solve/initialize/hyb-initialization q o\n"
            for j in range(len(heads)):
                result += f'''/define/named-expressions/edit "{heads[j]}" definition "{values[i][j]}[{self.
                input_variables_map[heads[j]]['unit']}]" q\n'''
            result += f"/solve/iterate {iteration_times}\n"

            # 这句话导出的是流场参数，注意填写正确的信息，如果你不需要流场数据的话需要把这一行删除
            result += f"/file/export/ascii F:/calculate_result/traindata/snapshots{i+1}.csv ({surface_input}) yes {user_input} q no\n"
            # todo 这一行你必须把result中添加所有你需要的物理量，然后把M,pout改成你需要的物理量名字，每行一个物理量，多余的需要删除
            if iswai == "y":
                result += f"/report/forces/wall-moments n dongye-hub dongye-pian dongye-wall () 0 0 0 0 0 -1 y ./external/M{i+1}.frp q\n"
                result += f"/report/surface-integrals/area-weighted-avg outletout () total-pressure y ./external/pout{i+1}.srp q\n"
        with open("./spell.jou", mode='w', encoding="utf-8") as fp:
            fp.write(result)
        messagebox.showinfo("提示", "已将代码写入./spell.jou，请将其注入fluent")

    @staticmethod
    def summon_surface_code():
        # 询问用户需要生成的几何面
        surface_input = simpledialog.askstring("输入需要求解的平面，空间求解可跳过", "以空格隔开")
        surfaces = surface_input.split(' ')
        result = ""
        for surface in surfaces:
            result += f"/file/export/ascii ./surfaces/{surface}.csv ({surface}) yes q no\n"
        with open("./surface.jou", mode='w', encoding='utf-8') as fp:
            fp.write(result)
        messagebox.showinfo("提示", "已将代码写入./surface.jou，请将其注入fluent")

    def compress_train_data(self):
        folder_path = filedialog.askdirectory()
        if not folder_path:
            messagebox.showerror("Error", "请输入训练集路径")
            return
        file_list = os.listdir(folder_path)
        if not file_list:
            messagebox.showerror("Error", "训练集路径下不能为空")
            return
        for filename in file_list:
            if not filename.endswith(".csv"):
                messagebox.showerror("Error", "训练集需要为csv格式")
                return
        if not self.compressed_sample_number_entry.get():
            messagebox.showerror("Error", "请指明单个训练样本采样点数（1000~5000为宜）")
            return
        # 读取文件之一
        df = pd.read_csv(folder_path+'/'+file_list[0])
        # 删除空字符串
        df = df.replace(r'^\s*$', np.nan, regex=True)
        df = df.dropna()
        n_points = int(self.compressed_sample_number_entry.get())
        # 获取坐标数据
        coords = df[['    x-coordinate', '    y-coordinate', '    z-coordinate']].values
        # 使用蒙特卡洛采样选择均匀的点
        indices = np.random.choice(len(coords), size=n_points, replace=False)
        # 删除第一行的空字符
        with open(folder_path + '/' + file_list[0], mode='r', encoding='utf-8') as file:
            first_line = file.readlines(1)
        column = [i.strip(" ") for i in first_line[0][:-1].split(',')]
        # 所有文件均采用此采样，压缩之后保存在该路径下的traindata文件夹中
        for i in range(len(file_list)):
            print(f"进度: {i+1}/{len(file_list)}")
            df = pd.read_csv(folder_path+'/'+file_list[i])
            df = df.replace(r'^\s*$', np.nan, regex=True)
            df = df.dropna()
            # 删除表头空字符
            df.columns = column
            compressed_df = df.iloc[indices]
            # 按照 nodenumber 从小到大排列数据
            df_sorted = compressed_df.sort_values(by='nodenumber')
            df_sorted.to_csv(f'./traindata/snapshots{i+1}.csv', index=False)

    def run(self):
        self.window.mainloop()


if __name__ == "__main__":
    gui = RBPstringGUI()
    gui.run()
