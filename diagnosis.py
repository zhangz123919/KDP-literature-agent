
from __future__ import annotations

import pandas as pd


VARIABLES = {
    "过饱和度": {
        "mechanism": "过高可能引起生长界面失稳、包裹体捕获和缺陷密度上升。",
        "experiment": "保持温度、籽晶和固定方式不变，仅设置低/中/高三档过饱和度。",
        "metric": "生长速率、包裹体密度、裂纹发生率、裂纹出现时间",
        "query": "supersaturation growth interface inclusion crack",
        "falsify": "改变过饱和度后缺陷密度和开裂行为无系统变化，则其作为主因的优先级应下降。",
        "record": "记录溶液浓度、温度、过饱和度估算、生长速率和裂纹时序。",
    },
    "降温速率": {
        "mechanism": "过快降温可能增加温度梯度与热应力，从而提高裂纹萌生风险。",
        "experiment": "保持晶体尺寸和固定方式一致，仅改变降温程序：慢/中/快三档。",
        "metric": "晶体温度曲线、裂纹出现温度/时间/位置、裂纹方向",
        "query": "cooling rate temperature gradient thermal stress crack",
        "falsify": "在可重复条件下显著改变降温速率但裂纹时序和概率不变，则需降低热应力主因判断。",
        "record": "连续记录降温曲线、环境温度、裂纹首次出现时刻与位置。",
    },
    "溶液杂质/纯度": {
        "mechanism": "杂质可进入晶格、改变生长台阶、形成局域吸收或促进夹杂形成。",
        "experiment": "原溶液与净化/高纯原料溶液进行单变量对照。",
        "metric": "杂质信号、包裹体/散射点密度、晶体质量、开裂率",
        "query": "impurity doping inclusion crystal growth crack laser damage",
        "falsify": "纯度显著改善后杂质信号下降但缺陷/开裂无变化，则杂质不是主要控制变量。",
        "record": "记录原料批次、纯化过程、杂质检测和对应晶体缺陷统计。",
    },
    "籽晶质量": {
        "mechanism": "籽晶原有裂纹、位错、包裹体或表面损伤可能向生长晶体传播或形成应力集中。",
        "experiment": "高质量籽晶与已知含缺陷籽晶对照，其余条件保持一致。",
        "metric": "裂纹起点与籽晶缺陷共定位率、位错/散射点延续性",
        "query": "seed crystal defect dislocation inclusion crack",
        "falsify": "不同籽晶质量组裂纹起点与概率无可重复差异，则籽晶缺陷主因优先级下降。",
        "record": "生长前保存籽晶显微图、取向、表面质量以及生长后裂纹共定位图。",
    },
    "籽晶类型/取向": {
        "mechanism": "不同取向会改变生长面、各向异性热膨胀和应力释放路径。",
        "experiment": "只改变籽晶取向/类型，保持生长和冷却流程一致。",
        "metric": "裂纹方向、开裂率、生长形貌、主晶面",
        "query": "seed orientation anisotropy thermal expansion crack KDP",
        "falsify": "不同取向下裂纹方向与发生率无统计趋势，则取向不是主要解释变量。",
        "record": "保存籽晶取向标定、晶体方位与裂纹方向之间的对应关系。",
    },
    "籽晶固定方式": {
        "mechanism": "刚性夹持或局部约束可能抑制自由收缩并造成固定点附近应力集中。",
        "experiment": "刚性固定与低约束固定对照。",
        "metric": "固定点附近裂纹概率、裂纹起点、冷却过程形变",
        "query": "mechanical constraint seed holder residual stress crack",
        "falsify": "显著降低固定约束后固定点附近裂纹仍无改善，则需转向材料内部缺陷或热梯度解释。",
        "record": "记录夹持位置、接触面积、材料、预紧程度及裂纹起点。",
    },
    "生长温度稳定性": {
        "mechanism": "温度波动会改变过饱和度、传质和生长界面稳定性，可能诱发生长条纹与缺陷波动。",
        "experiment": "原控温条件与优化控温条件对照。",
        "metric": "温度波动幅度、条纹/缺陷密度、开裂率",
        "query": "temperature fluctuation supersaturation growth interface defect KDP",
        "falsify": "温度稳定性显著提高但缺陷密度和开裂无改善，则温度波动不是主要瓶颈。",
        "record": "保存高时间分辨率温度日志，不只记录设定值。",
    },
    "出炉/取晶冷却": {
        "mechanism": "取晶后的突变温差、表面蒸发和环境交换可能引入附加热应力。",
        "experiment": "原流程与分阶段缓冷/受控环境冷却对照。",
        "metric": "冷却曲线、裂纹首次出现时间、表面状态",
        "query": "cooling thermal stress crystal crack KDP",
        "falsify": "缓冷显著改变温度梯度但裂纹行为不变，则需优先排查内部缺陷和机械约束。",
        "record": "从取晶前开始记录温度直至室温，并同步拍摄裂纹出现时刻。",
    },
    "晶体尺寸/生长阶段": {
        "mechanism": "晶体尺寸增加会改变流动、传质、表面过饱和度和热扩散时间尺度；大体积还会提高包含较大缺陷的统计概率。",
        "experiment": "在同一或尽量相同名义工艺下设置小/中/大三个尺寸阶段，并同步比较缺陷和局部场。",
        "metric": "尺寸、质量、表面过饱和度均匀性、白纹密度、串丝密度、包裹体密度、开裂概率",
        "query": "large scale KDP crystal size mass transfer surface supersaturation defect crack",
        "falsify": "在足够尺寸跨度和重复批次下，局部场、缺陷密度及开裂行为均无系统尺寸趋势，则需降低尺度效应主因优先级。",
        "record": "记录三维尺寸、质量、生长时间，并标记白纹/串丝首次出现时对应的尺寸与日期。",
    },
    "晶体旋转/流场": {
        "mechanism": "转速、换向周期、循环方式与晶体尺寸共同决定流动分离、回流、表面剪切和浓度边界层，从而改变晶面局部供料。",
        "experiment": "保持溶液和温度程序不变，在固定尺寸阶段改变转速/换向/循环方式；或利用CFD选择可比工况。",
        "metric": "流速/涡流、表面过饱和度均匀性、生长速率波动、白纹/串丝/包裹体密度",
        "query": "KDP crystal rotation hydrodynamics mass transfer surface supersaturation inclusion",
        "falsify": "显著改变流场后局部供料和缺陷分布均无可重复变化，则流场作为主控制变量的优先级下降。",
        "record": "保存转速、换向程序、循环流量/搅拌方式、槽体构型和晶体对应尺寸。",
    },
    "传质/表面过饱和度均匀性": {
        "mechanism": "体相过饱和度相同并不保证晶面表面过饱和度相同；局部低过饱和度、梯度和波动可导致台阶聚集、形貌不稳和母液俘获。",
        "experiment": "用CFD/传质模型或可观测代理量比较不同尺寸/流动工况的表面过饱和度均值、标准差和低值区。",
        "metric": "表面过饱和度均值/标准差、低过饱和区面积、生长速率波动、macrostep/包裹体/白纹/串丝",
        "query": "surface supersaturation mass transfer macrostep liquid inclusion KDP",
        "falsify": "若局部过饱和度均匀性明显改善但界面形貌和缺陷无改善，则需转向位错、杂质或其他机制。",
        "record": "记录模型版本、边界条件、表面过饱和度统计量，并与真实缺陷坐标做共定位。",
    },
    "包裹体/散射点": {
        "mechanism": "包裹体与基体之间的结构/热物性不连续可形成局域应变、散射或潜在裂纹萌生位置。",
        "experiment": "比较高/低包裹体密度样品，并进行裂纹起点共定位。",
        "metric": "包裹体密度、裂纹起点共定位率、散射强度",
        "query": "solution inclusion scattering center local strain crack KDP",
        "falsify": "裂纹起点与包裹体长期缺乏空间共定位，且高/低密度组无差异，则该机制需降级。",
        "record": "建立同一区域生长前后/开裂前后的显微或散射共定位图。",
    },
}


STATE_SCORE = {
    "明显异常": 3,
    "偏高/偏快/强约束": 3,
    "可疑": 2,
    "一般/不确定": 2,
    "较好/稳定": 1,
    "偏低/偏慢/低约束": 1,
    "未知": 0,
}


def diagnose(states):
    """
    这里给出的是“工艺先验风险排序”，不是因果结论。
    文献证据强度由页面层另外检索并绑定，避免把规则分数伪装成实验事实。
    """
    rows = []

    for variable, meta in VARIABLES.items():
        state = states.get(variable, "未知")
        n = STATE_SCORE.get(state, 0)
        risk = "高" if n == 3 else "中" if n == 2 else "低" if n == 1 else "待核"

        rows.append(
            {
                "变量": variable,
                "当前状态": state,
                "风险": risk,
                "风险分": n,
                "判断性质": "工艺先验排序（非因果结论）",
                "可能机理": meta["mechanism"],
                "最小对照实验": meta["experiment"],
                "关键指标": meta["metric"],
                "否证判据": meta["falsify"],
                "记录要求": meta["record"],
                "检索关键词": meta["query"],
            }
        )

    return pd.DataFrame(rows).sort_values(
        ["风险分", "变量"],
        ascending=[False, True],
    )


def experiment_matrix(selected, baseline=""):
    rows = []

    for variable in selected:
        meta = VARIABLES[variable]
        rows.append(
            {
                "变量": variable,
                "基线组": baseline or "当前标准流程",
                "实验组": meta["experiment"],
                "保持不变": "除该变量外，其余生长、冷却、取样和表征流程保持一致",
                "关键指标": meta["metric"],
                "探索阶段重复": "建议每组≥3个独立样品/批次；正式统计根据方差/效应量追加",
                "支持判据": "变量变化后，预设关键指标出现方向一致且可重复的变化",
                "否证判据": meta["falsify"],
                "记录要求": meta["record"],
            }
        )

    return pd.DataFrame(rows)
