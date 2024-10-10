import os
import uuid
import pandas as pd
from dash import html, dcc
import feffery_antd_charts as fact
import feffery_antd_components as fac
import feffery_utils_components as fuc
from feffery_dash_utils.style_utils import style
from dash.dependencies import Input, Output, State

from server import app


import pandas as pd

# 读取 Excel 数据
df = pd.read_excel('data.xlsx')

# 初始化存储转换结果的列表
version_data = []

# 将 DataFrame 中每一行转换为目标格式
for index, row in df.iterrows():
    # 添加不同模型的值作为各自的label
    version_data.append({
        "timing": row['timing'],
        "label": "真实值",
        "value": row['真实值'],
    })
    version_data.append({
        "timing": row['timing'],
        "label": "MST-Former",
        "value": row['MST-Former'],
    })
    version_data.append({
        "timing": row['timing'],
        "label": "LSTM",
        "value": row['LSTM'],
    })
    version_data.append({
        "timing": row['timing'],
        "label": "BP",
        "value": row['BP'],
    })


# 生成tooltip标题字段
version_data = [
    {
        **item,
        "title_field": "{}".format(item["timing"]),
    }
    for item in version_data
]

# 示例全局数据临时存储
GLOBAL_DATA = {}

# 函数式layout，确保每次用户访问应用时，即时生成唯一的会话数据唯一识别id
app.layout = lambda: html.Div(
    [
        # 当前会话数据唯一识别id
        dcc.Store(id="current-active-data-key", data=str(uuid.uuid4())),
        # 监听页面关闭/刷新事件
        fuc.FefferyListenUnload(id="listen-unload"),
        # 经典的垂直排列布局
        fac.AntdSpace(
            [
                # 文件上传
                fac.AntdDraggerUpload(
                    id="upload-file",
                    apiUrl="/upload",
                    text="数据文件上传",
                    hint="以接受XLSX格式文件为例",
                    fileTypes=["xlsx"],
                    fileListMaxLength=1,  # 限定上传记录列表长度至多为1
                ),
                # 内容容器
                html.Div(id="content-container"),
            ],
            direction="vertical",
            style=style(width="100%"),
        ),
    ],
    style=style(padding="50px 100px"),
)


@app.callback(
    Output("content-container", "children"),
    Input("upload-file", "listUploadTaskRecord"),
    State("current-active-data-key", "data"),
)
def update_content(listUploadTaskRecord, data_key):
    """处理上传文件后的渲染内容更新"""

    # 若本次上传任务有效
    if listUploadTaskRecord and listUploadTaskRecord[0]["taskStatus"] == "success":
        # 根据listUploadTaskRecord中的已上传文件路径信息，读取数据并基于data_key作为键，存储到GLOBAL_DATA中
        GLOBAL_DATA[data_key] = pd.read_excel(
            os.path.join(
                "caches",
                listUploadTaskRecord[0]["taskId"],
                listUploadTaskRecord[0]["fileName"],
            )
        ).sort_values("date", ascending=True)

        # 返回一图一表渲染内容示例
        return fac.AntdTabs(
            items=[
                {
                    "label": "可视化",
                    "key": "可视化",
                    "children": html.Div(
                        # fact.AntdLine(
                        #     data=GLOBAL_DATA[data_key].to_dict("records"),
                        #     xField="date",
                        #     yField="close",
                        #     slider={},
                        # ),
                        fact.AntdLine(
                            data=version_data,
                            xField="timing",  # x轴的数据
                            yField="value",  # y轴数据
                            seriesField="label",  # title
                            xAxis=True,  # False 不显示横坐标内容
                            yAxis={
                                "min": 700000,  # 设置y轴最小值
                                "max": 900000  # 设置y轴最大值
                            },
                            meta={
                                "timing": {
                                    "type": "cat"
                                }
                            },
                            legend={
                                "position": "right-top"
                            },
                            smooth=True,
                            animation={
                                "appear": {
                                    "animation": "path-in",
                                    "duration": 3000,
                                },
                            },
                            tooltip={
                                "title": "title_field"  # 传入充当tooltip标题的字段名
                            },
                        ),
                        style=style(height=500),
                    ),
                },
                {
                    "label": "数据表",
                    "key": "数据表",
                    "children": fac.AntdSpace(
                        [
                            fac.AntdSelect(
                                id="show-data-counts",
                                options=["最近10条", "最近50条", "全量"],
                                value="最近10条",
                                allowClear=False,
                                style=style(width=200),
                            ),
                            fac.AntdTable(
                                id="data-table",
                                columns=[
                                    {"dataIndex": column, "title": column}
                                    for column in GLOBAL_DATA[data_key].columns
                                ],
                            ),
                        ],
                        direction="vertical",
                        style=style(width="100%"),
                    ),
                },
            ],
            centered=True,
            size="large",
        )

    return fac.AntdResult(status="info", subTitle="请先上传能源系统的数据文件")


@app.callback(
    Output("data-table", "data"),
    Input("show-data-counts", "value"),
    State("current-active-data-key", "data"),
)
def update_table(show_data_counts, current_active_data_key):
    """基于服务端存储的临时数据，处理表格标签页中的数据交互更新"""

    if current_active_data_key:
        if show_data_counts == "最近10条":
            return GLOBAL_DATA[current_active_data_key].head(10).to_dict("records")
        elif show_data_counts == "最近50条":
            return GLOBAL_DATA[current_active_data_key].head(50).to_dict("records")
        else:
            return GLOBAL_DATA[current_active_data_key].to_dict("records")

    return None


@app.callback(
    Input("listen-unload", "unloaded"),
    State("current-active-data-key", "data"),
)
def destroy_temp_data(unloaded, data_key):
    """在用户关闭应用后，销毁存储在服务端的临时数据"""

    if data_key in GLOBAL_DATA:
        del GLOBAL_DATA[data_key]


if __name__ == "__main__":
    app.run(
        host='0.0.0.0',  # 使应用可以通过本地网络访问
        port=7656,  # 自定义端口号
        debug=False  # 关闭调试模式以提升性能
    )
