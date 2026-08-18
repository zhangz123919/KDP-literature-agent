from __future__ import annotations

import pandas as pd
import streamlit as st

from research_memory import add_item
from ui import page_header, section_title, soft_note


METHODS = [
    {
        "category": "晶体取向与结构",
        "name": "X射线晶体定向 / Laue",
        "instrument": "X射线晶体定向仪、Laue背反射系统",
        "measure": "晶轴方向、晶面取向、切样方向",
        "sample": "完整晶体或定向切块；保留生长方向和籽晶方向信息",
        "raw": "衍射斑点图 / 定向角度",
        "derived": "[001]、[100]、[110]等方向；(001)、(100)/(200)、(101)等晶面关系",
        "use": "所有定向物性、力学、缺陷空间定位的前置步骤",
        "priority": "基础必做",
        "destructive": "否",
        "note": "以后不要只记录“200样品”，要分开写样品表面晶面与测试/载荷方向。",
    },
    {
        "category": "晶体取向与结构",
        "name": "高分辨XRD / 摇摆曲线",
        "instrument": "高分辨X射线衍射仪 HRXRD",
        "measure": "晶格参数、衍射峰、摇摆曲线、结晶完整性与局部应变线索",
        "sample": "定向平整晶片；记录取样位置和生长扇区",
        "raw": "2θ-ω扫描、ω摇摆曲线、峰形",
        "derived": "FWHM、峰位偏移、晶格参数、区域差异",
        "use": "比较白纹区/透明区、不同尺寸阶段的晶格完整性",
        "priority": "重点",
        "destructive": "低",
        "note": "峰展宽或峰位变化只能说明结构/应变差异线索，不能单独证明缺陷微观类型。",
    },
    {
        "category": "晶体取向与结构",
        "name": "X射线形貌术（X-ray topography）",
        "instrument": "实验室或同步辐射X射线形貌成像系统",
        "measure": "位错、应变场、生长扇区边界、生长条纹等二维结构缺陷",
        "sample": "薄片/窗口样；必须保留晶向与空间位置",
        "raw": "形貌像",
        "derived": "位错分布、条纹/扇区边界、局域畸变空间位置",
        "use": "对白纹是否伴随位错/生长条纹/应变异常进行结构验证",
        "priority": "条件允许时重点",
        "destructive": "低-中",
        "note": "很适合把肉眼白纹与内部结构缺陷做空间对应。",
    },
    {
        "category": "缺陷与显微",
        "name": "透射 / 侧光 / 暗场宏观成像",
        "instrument": "稳定光源、相机、标尺、可旋转载台；必要时激光片光源",
        "measure": "肉眼白纹、串丝、包裹体、宏观裂纹的数量、位置、方向与密度",
        "sample": "整块晶体优先；尽量在切样前完成",
        "raw": "多角度原始照片/视频",
        "derived": "白纹密度、长度、宽度、间距；串丝长度/数量/角度；裂纹位置",
        "use": "建立缺陷空间地图和生长历史对应关系",
        "priority": "基础必做",
        "destructive": "否",
        "note": "固定光源、相机、距离、曝光和晶体方向，才能做跨批次比较。",
    },
    {
        "category": "缺陷与显微",
        "name": "光学显微镜",
        "instrument": "明场/暗场光学显微镜",
        "measure": "微包裹体、微裂纹、串丝组成、白纹区域微观形貌",
        "sample": "表面平整观察窗或切片；避免水基清洗",
        "raw": "不同倍率显微照片",
        "derived": "颗粒尺寸、包裹体密度、裂纹长度、链状结构组成",
        "use": "把宏观“白纹/串丝”拆解为可定量微观结构",
        "priority": "基础必做",
        "destructive": "低",
        "note": "白纹是现象名，在显微结构确认前不要预设它一定是哪一类缺陷。",
    },
    {
        "category": "缺陷与显微",
        "name": "偏光 / 应力双折射成像",
        "instrument": "偏光显微镜、偏振应力观察系统、偏光成像装置",
        "measure": "残余应力、局部应变和光学各向异性异常的空间分布",
        "sample": "透明晶片或可透光晶块",
        "raw": "交叉偏振图像、相位/光程差信息（设备支持时）",
        "derived": "应力条纹、区域应力差异、缺陷周围应变热点",
        "use": "验证白纹/串丝附近是否伴随局部应力异常，并与开裂位置比较",
        "priority": "重点",
        "destructive": "否/低",
        "note": "定量应力需要光弹常数、厚度和标定；普通偏光图首先用于相对比较。",
    },
    {
        "category": "缺陷与显微",
        "name": "激光散射成像",
        "instrument": "低功率激光散射检测系统 / 片光照明 + 相机",
        "measure": "体内散射中心、微包裹体、串丝及其空间轨迹",
        "sample": "透明晶体或光学窗口样",
        "raw": "散射图像/视频、角度依赖图",
        "derived": "散射点密度、串丝路径、散射强度相对分布",
        "use": "串丝与体内包裹体的快速定位；建立缺陷3D位置近似",
        "priority": "重点",
        "destructive": "否",
        "note": "散射强弱受光路和表面质量影响，跨样品比较必须保持光学条件一致。",
    },
    {
        "category": "缺陷与显微",
        "name": "X-ray CT / 显微CT",
        "instrument": "工业CT或微米CT",
        "measure": "内部体缺陷、裂纹、较大包裹体的三维空间分布",
        "sample": "尺寸受设备视野/分辨率限制的晶块",
        "raw": "断层投影与重建体数据",
        "derived": "缺陷体积、位置、连通性、裂纹3D路径",
        "use": "需要三维验证白纹/包裹体/裂纹空间关系时使用",
        "priority": "进阶",
        "destructive": "否",
        "note": "微小低对比缺陷是否可见取决于分辨率和密度/吸收差，不应预设CT一定能看到所有白纹。",
    },
    {
        "category": "成分与杂质",
        "name": "ICP-MS / ICP-OES",
        "instrument": "电感耦合等离子体质谱/发射光谱",
        "measure": "Fe、Al、Cr等痕量/微量元素杂质",
        "sample": "取样溶解；同时建议测试母液和晶体不同区域",
        "raw": "元素浓度信号",
        "derived": "杂质浓度、批次差异、晶体/母液分配关系",
        "use": "研究杂质是否与白纹、缺陷密度、生长速率或光学质量相关",
        "priority": "重点",
        "destructive": "是",
        "note": "必须设置空白、标准和重复样；对KDP母液与晶体样要分别记录取样位置。",
    },
    {
        "category": "成分与杂质",
        "name": "离子色谱 / 水溶液化学分析",
        "instrument": "离子色谱仪、酸碱滴定/电导率等辅助设备",
        "measure": "母液中阴阳离子杂质、溶液化学状态",
        "sample": "生长母液或取样溶液",
        "raw": "色谱峰、浓度",
        "derived": "离子杂质谱、批次变化",
        "use": "追踪生长液污染和补液/循环导致的化学变化",
        "priority": "按问题选做",
        "destructive": "样液消耗",
        "note": "用于溶液过程控制，不替代晶体内部杂质空间表征。",
    },
    {
        "category": "成分与杂质",
        "name": "Raman 光谱 / 显微Raman",
        "instrument": "拉曼光谱仪、共焦显微Raman",
        "measure": "PO4振动、局域结构、包裹体内容物及应变/结构变化线索",
        "sample": "晶体表面或可聚焦内部区域",
        "raw": "Raman谱、面扫/线扫",
        "derived": "峰位、峰宽、强度比、区域映射",
        "use": "白纹区 vs 透明区；串丝包裹体内容物与周围晶格比较",
        "priority": "重点",
        "destructive": "否/低",
        "note": "激光功率要控制，避免局部加热或损伤。",
    },
    {
        "category": "成分与杂质",
        "name": "FTIR 红外光谱",
        "instrument": "傅里叶变换红外光谱仪（透射/ATR按样品条件）",
        "measure": "OH/氢键相关振动、杂质/官能团与结构差异",
        "sample": "薄片或适合红外光路的样品",
        "raw": "红外吸收谱",
        "derived": "峰位、峰强、区域差异",
        "use": "补充氢键/结构及污染信息；与Raman交叉验证",
        "priority": "按问题选做",
        "destructive": "低",
        "note": "用于结构/化学信息，不直接等价于宏观白纹形成机制。",
    },
    {
        "category": "光学性能",
        "name": "UV-Vis-NIR 透过/吸收光谱",
        "instrument": "紫外-可见-近红外分光光度计",
        "measure": "透过率、吸收边、附加吸收和批次光学质量",
        "sample": "厚度已知、两面质量可控的定向晶片",
        "raw": "T(λ)、A(λ)",
        "derived": "透过率、吸收系数（需要厚度/反射修正时说明）",
        "use": "比较白纹区、串丝区、正常区及不同尺寸晶体的光学均匀性",
        "priority": "重点",
        "destructive": "低",
        "note": "表面粗糙、散射和厚度都会影响透过率，必须保存样品厚度与表面状态。",
    },
    {
        "category": "光学性能",
        "name": "弱吸收 / 光热检测",
        "instrument": "光热共路干涉 PCI、光热偏转等弱吸收系统",
        "measure": "极低吸收、吸收前驱体空间分布",
        "sample": "光学质量较好的样片/晶块",
        "raw": "光热信号、二维扫描图",
        "derived": "弱吸收系数、热点分布",
        "use": "高功率激光应用前评估吸收缺陷；与包裹体/杂质/白纹空间相关",
        "priority": "高功率光学专项",
        "destructive": "否/低",
        "note": "需要严格标定和洁净光路；结果更适合与LIDT/散射联合分析。",
    },
    {
        "category": "光学性能",
        "name": "干涉仪 / 波前检测",
        "instrument": "Fizeau干涉仪、波前传感系统",
        "measure": "透射波前、光学均匀性、折射率/厚度非均匀引起的波前畸变",
        "sample": "光学加工样片/大口径窗口样",
        "raw": "干涉图、波前图",
        "derived": "PV、RMS、区域波前畸变",
        "use": "判断白纹/生长带是否最终影响大口径光学均匀性",
        "priority": "光学质量重点",
        "destructive": "否",
        "note": "需要把材料内部不均匀和表面面形误差区分开。",
    },
    {
        "category": "光学性能",
        "name": "LIDT 激光损伤阈值",
        "instrument": "标准化激光损伤测试平台",
        "measure": "不同区域/批次的激光诱导损伤阈值和损伤概率",
        "sample": "表面状态严格受控的测试片",
        "raw": "能量密度、损伤事件、概率曲线、损伤形貌",
        "derived": "LIDT、损伤概率、区域差异",
        "use": "验证串丝、包裹体、弱吸收热点等是否降低激光耐受性",
        "priority": "激光应用专项",
        "destructive": "是",
        "note": "必须记录波长、脉宽、光斑、测试协议和表面加工状态，否则数值不可直接横向比较。",
    },
    {
        "category": "热物性",
        "name": "TMA / 热膨胀测试",
        "instrument": "热机械分析仪、推杆式膨胀仪",
        "measure": "不同晶向线膨胀系数 α(T)",
        "sample": "定向长条；优先 [001]、[100]，必要时[110]",
        "raw": "L(T)、ΔL/L",
        "derived": "α(T)",
        "use": "热应变和热应力模型输入",
        "priority": "基础必做",
        "destructive": "低",
        "note": "测试温区尽量覆盖实际生长取晶/冷却范围；记录升降温速率。",
    },
    {
        "category": "热物性",
        "name": "DSC 比热测试",
        "instrument": "差示扫描量热仪 DSC",
        "measure": "比热容 Cp(T)、热事件",
        "sample": "小块定量样品；表面与环境状态一致",
        "raw": "热流-温度曲线",
        "derived": "Cp(T)",
        "use": "瞬态热传导模型输入",
        "priority": "基础必做",
        "destructive": "低",
        "note": "与LFA和密度联合得到热导率。",
    },
    {
        "category": "热物性",
        "name": "LFA 激光闪射",
        "instrument": "激光闪射热扩散仪",
        "measure": "热扩散率 a(T)",
        "sample": "定向薄片/圆片，使热流分别沿[001]和[100]",
        "raw": "背面温升响应曲线",
        "derived": "a(T)，进一步 k=aρCp",
        "use": "温度场与热导各向异性模型",
        "priority": "基础必做",
        "destructive": "低",
        "note": "样品表面处理、涂层策略和KDP耐受性需要按设备规范确认。",
    },
    {
        "category": "热物性",
        "name": "密度测试",
        "instrument": "精密天平、几何尺寸测量；必要时采用与KDP兼容的专用密度方案",
        "measure": "ρ",
        "sample": "规则样品",
        "raw": "质量、尺寸/体积",
        "derived": "密度 ρ",
        "use": "热传导、热导率换算及其他模型输入",
        "priority": "基础必做",
        "destructive": "否",
        "note": "KDP水溶性，避免直接使用会溶解/腐蚀样品的液体排液法。",
    },
    {
        "category": "力学与断裂",
        "name": "RUS / 超声弹性常数",
        "instrument": "共振超声谱 RUS、超声脉冲回波系统",
        "measure": "完整/部分弹性常数 Cij、声速",
        "sample": "定向规则单晶块，尺寸和质量准确",
        "raw": "共振频率谱 / 声速",
        "derived": "C11、C12、C13、C33、C44、C66等",
        "use": "各向异性热-力耦合本构模型",
        "priority": "重点",
        "destructive": "否/低",
        "note": "比只给一个E和ν更适合KDP各向异性有限元。",
    },
    {
        "category": "力学与断裂",
        "name": "三点弯曲 / 定向强度",
        "instrument": "电子万能试验机 + 三点弯曲夹具",
        "measure": "弯曲破坏强度、离散性、方向差异",
        "sample": "[001]、[100]、[110]定向梁；表面加工一致；每方向多根重复",
        "raw": "载荷-位移曲线、破坏载荷",
        "derived": "σf、Weibull统计（样本足够时）",
        "use": "与有限元最大主拉应力/失效指标比较",
        "priority": "基础必做",
        "destructive": "是",
        "note": "脆性材料强度对表面划痕和内部缺陷非常敏感，必须做重复和失效位置记录。",
    },
    {
        "category": "力学与断裂",
        "name": "应变片 / DIC 变形测量",
        "instrument": "应变片系统、数字图像相关 DIC",
        "measure": "纵向/横向应变、方向弹性模量E、泊松比ν",
        "sample": "定向力学试样；DIC需要合适表面散斑",
        "raw": "载荷-应变、全场位移/应变",
        "derived": "E、ν、局部应变集中",
        "use": "简化弹性模型、缺陷附近应变场验证",
        "priority": "按方案选择",
        "destructive": "通常随力学测试",
        "note": "泊松比必须同时写明载荷方向和横向测量方向。",
    },
    {
        "category": "力学与断裂",
        "name": "SENB 断裂韧性",
        "instrument": "万能试验机 + 单边缺口梁夹具/断裂测试系统",
        "measure": "断裂韧性 KIC 或等效断裂参数",
        "sample": "定向缺口梁；明确裂纹面与扩展方向",
        "raw": "载荷-位移、临界载荷、断口",
        "derived": "KIC、方向依赖、温度/速率依赖",
        "use": "判断已有微裂纹或缺陷在应力场下是否失稳扩展",
        "priority": "重点",
        "destructive": "是",
        "note": "不能只写“[110]样品”，断裂实验方向描述要包含裂纹面和裂纹扩展方向。",
    },
    {
        "category": "力学与断裂",
        "name": "显微硬度 / 纳米压痕",
        "instrument": "显微硬度计、纳米压痕仪",
        "measure": "局部硬度、接触模量、局部力学差异",
        "sample": "表面平整、定向样片",
        "raw": "压痕曲线/压痕形貌",
        "derived": "硬度、接触模量、区域差异",
        "use": "比较白纹区/正常区或不同生长扇区的局部力学响应",
        "priority": "进阶",
        "destructive": "微损伤",
        "note": "局部压痕结果不能直接替代宏观破坏强度和断裂韧性。",
    },
    {
        "category": "生长过程监测",
        "name": "温度连续记录",
        "instrument": "高精度温控器、Pt100/热电偶、多点温度采集系统",
        "measure": "溶液/环境/关键位置温度、波动、降温速率",
        "sample": "生长过程在线",
        "raw": "T(t)多通道时间序列",
        "derived": "降温速率、波动幅度、异常事件、阶段平均/梯度",
        "use": "把白纹/串丝/开裂对应回具体生长时间和晶体尺寸阶段",
        "priority": "基础必做",
        "destructive": "否",
        "note": "时间戳必须与转速、换向、流量、晶体尺寸记录统一。",
    },
    {
        "category": "生长过程监测",
        "name": "溶液浓度 / 饱和度跟踪",
        "instrument": "折光/密度/取样化学分析等适用方法 + 溶解度曲线",
        "measure": "体相浓度、饱和温度、体相过饱和度",
        "sample": "生长母液",
        "raw": "浓度/折射率/密度/温度数据",
        "derived": "体相过饱和度 σbulk(t)",
        "use": "判断名义过饱和度是否稳定，并作为CFD传质边界条件",
        "priority": "基础必做",
        "destructive": "少量取样",
        "note": "体相过饱和度不等于晶体表面局部过饱和度；后者需要传质模型/局部测量解释。",
    },
    {
        "category": "生长过程监测",
        "name": "转速 / 换向 / 循环流量记录",
        "instrument": "电机控制器、转速计、流量计、PLC/日志系统",
        "measure": "rpm、换向周期、加减速、循环流量和异常",
        "sample": "生长过程在线",
        "raw": "rpm(t)、flow(t)、程序事件",
        "derived": "阶段工况、异常次数、尺寸对应工况",
        "use": "大尺寸尺度效应CFD边界条件与缺陷溯源",
        "priority": "基础必做",
        "destructive": "否",
        "note": "同样rpm不代表小晶体和大晶体局部流动相同，所以必须与晶体尺寸同步记录。",
    },
    {
        "category": "生长过程监测",
        "name": "生长过程视觉记录 / 尺寸测量",
        "instrument": "相机、标尺/视觉测量、称量或几何尺寸记录系统",
        "measure": "晶体尺寸、晶面演化、宏观异常、生长速率",
        "sample": "生长过程分阶段",
        "raw": "照片/视频、三维尺寸、质量、时间戳",
        "derived": "L(t)、质量增长、生长速率、缺陷首次出现阶段",
        "use": "建立小→中→大尺寸数据库，并把空间位置反推到生长时间",
        "priority": "基础必做",
        "destructive": "否",
        "note": "缺陷研究最重要的不是只拍最终晶体，而是保留“什么时候开始出现”的过程证据。",
    },
]


PROBLEM_WORKFLOWS = {
    "肉眼大量白纹": {
        "question": "白纹到底是生长条纹/带状散射、局部应变，还是微包裹体富集等其他结构？",
        "first": ["透射 / 侧光 / 暗场宏观成像", "光学显微镜", "偏光 / 应力双折射成像"],
        "second": ["激光散射成像", "高分辨XRD / 摇摆曲线", "Raman 光谱 / 显微Raman"],
        "advanced": ["X射线形貌术（X-ray topography）", "X-ray CT / 显微CT"],
        "must": "晶向、白纹位置/方向/宽度/间距、距籽晶距离、所在生长扇区、对应生长时间与尺寸阶段。",
        "boundary": "在结构证据确认前，白纹只作为“宏观可见条带状光学不均匀现象”记录，不预设唯一微观机制。",
    },
    "串丝 / 发丝状包裹体": {
        "question": "串丝由什么微包裹体组成、沿什么方向分布、与位错/流场/局部传质是否空间对应？",
        "first": ["透射 / 侧光 / 暗场宏观成像", "激光散射成像", "光学显微镜"],
        "second": ["Raman 光谱 / 显微Raman", "偏光 / 应力双折射成像", "高分辨XRD / 摇摆曲线"],
        "advanced": ["X射线形貌术（X-ray topography）", "X-ray CT / 显微CT"],
        "must": "串丝数量、长度、角度、三维位置近似、晶向、晶面/扇区、首次出现尺寸阶段、附近白纹/裂纹情况。",
        "boundary": "串丝与位错、流场的共现可以提出机制假设，但要用空间对应与生长过程/模拟进一步验证。",
    },
    "开裂 / 裂纹萌生": {
        "question": "裂纹起点在哪里、沿什么晶面/方向扩展，是热应力主导还是局部缺陷提供了应力集中？",
        "first": ["透射 / 侧光 / 暗场宏观成像", "偏光 / 应力双折射成像", "X射线晶体定向 / Laue"],
        "second": ["三点弯曲 / 定向强度", "RUS / 超声弹性常数", "TMA / 热膨胀测试", "LFA 激光闪射", "DSC 比热测试"],
        "advanced": ["SENB 断裂韧性", "X-ray CT / 显微CT", "X射线形貌术（X-ray topography）"],
        "must": "裂纹起点、方向/晶面、发生时间、冷却/取晶温度历史、样品尺寸、附近白纹/串丝/包裹体。",
        "boundary": "不能仅凭最终裂纹形貌判断原因；必须把失效位置与温度场、应力场、物性和原始缺陷共同分析。",
    },
    "小晶体到大晶体尺度效应": {
        "question": "外部设定相同后，晶体尺寸增大是否改变局部流动、传质和表面环境，并导致缺陷概率变化？",
        "first": ["温度连续记录", "溶液浓度 / 饱和度跟踪", "转速 / 换向 / 循环流量记录", "生长过程视觉记录 / 尺寸测量"],
        "second": ["透射 / 侧光 / 暗场宏观成像", "激光散射成像", "偏光 / 应力双折射成像"],
        "advanced": ["高分辨XRD / 摇摆曲线", "X射线形貌术（X-ray topography）"],
        "must": "晶体L(t)、质量/生长速率、温度、体相过饱和度、rpm/换向/流量、白纹/串丝/包裹体/开裂时空数据。",
        "boundary": "同样rpm或降温程序不代表表面局部环境相同；局部场需要CFD/传质模型与实验数据共同解释。",
    },
    "杂质是否导致缺陷": {
        "question": "不同批次或不同区域的缺陷变化，是否与母液/晶体中的杂质浓度和局部结构改变相关？",
        "first": ["ICP-MS / ICP-OES", "离子色谱 / 水溶液化学分析", "Raman 光谱 / 显微Raman"],
        "second": ["FTIR 红外光谱", "UV-Vis-NIR 透过/吸收光谱"],
        "advanced": ["弱吸收 / 光热检测"],
        "must": "母液批次、取样时间、晶体取样位置、生长扇区、杂质浓度、对应缺陷密度与光学数据。",
        "boundary": "相关性不等于因果；需要受控加杂/净化对照实验验证。",
    },
    "光学质量 / 激光损伤": {
        "question": "白纹、串丝、包裹体或杂质是否真正影响透过、波前、弱吸收和LIDT？",
        "first": ["UV-Vis-NIR 透过/吸收光谱", "激光散射成像", "干涉仪 / 波前检测"],
        "second": ["弱吸收 / 光热检测", "Raman 光谱 / 显微Raman"],
        "advanced": ["LIDT 激光损伤阈值"],
        "must": "测试区域位置、样品厚度、表面加工、晶向、缺陷类型/密度、激光参数与测试协议。",
        "boundary": "不同实验室LIDT不能只看一个数字横向比较，必须同时比较波长、脉宽、光斑、表面状态和统计协议。",
    },
}


CATEGORY_ORDER = [
    "晶体取向与结构",
    "缺陷与显微",
    "成分与杂质",
    "光学性能",
    "热物性",
    "力学与断裂",
    "生长过程监测",
]


def _df() -> pd.DataFrame:
    return pd.DataFrame(METHODS)


def _page_link(key: str, label: str, icon: str | None = None):
    page = (st.session_state.get("_kdp_nav_pages") or {}).get(key)
    if page is not None:
        st.page_link(page, label=label, icon=icon, width="stretch")


def _overview():
    st.markdown("### 先理解：不是‘有什么仪器就测什么’")
    st.write(
        "KDP大尺寸晶体研究应该从**科学问题**反推测试。先确认要解释的是白纹、串丝、尺度效应、热应力还是光学质量，再选择能提供判别证据的技术。"
    )
    st.markdown(
        "**推荐证据链：宏观定位 → 微观/结构确认 → 成分或物性 → 生长过程对应 → 计算/对照实验验证。**"
    )
    st.dataframe(
        pd.DataFrame(
            [
                ["晶体取向与结构", "方向、位错、晶格完整性、生长条纹/扇区", "X射线定向、HRXRD、X-ray topography"],
                ["缺陷与显微", "白纹、串丝、包裹体、裂纹在哪里、长什么样", "透射/侧光、显微、偏光、激光散射、CT"],
                ["成分与杂质", "缺陷里面/周围是什么，母液是否污染", "ICP、离子色谱、Raman、FTIR"],
                ["光学性能", "缺陷是否真正影响光学使用性能", "UV-Vis-NIR、弱吸收、波前、LIDT"],
                ["热物性", "温度怎么在大晶体中传播", "TMA、DSC、LFA、密度"],
                ["力学与断裂", "热应变怎么转为应力，什么时候会断", "RUS、弯曲、DIC、SENB"],
                ["生长过程监测", "缺陷是在什么时候、什么尺寸阶段产生", "温度、浓度、转速/流量、尺寸/视频连续记录"],
            ],
            columns=["测试体系", "主要回答", "典型技术"],
        ),
        hide_index=True,
        width="stretch",
    )
    soft_note(
        "尤其对白纹：先把它当作可见现象做空间定量，再用显微、偏光、散射、XRD/形貌术等逐步判别。不要因为肉眼叫‘白纹’，就在数据库里提前指定微观成因。"
    )


def _problem_route():
    st.markdown("### 我遇到了一个问题，该先测什么？")
    problem = st.selectbox("选择当前研究问题", list(PROBLEM_WORKFLOWS), key="testing_problem")
    p = PROBLEM_WORKFLOWS[problem]
    st.markdown(f"## {problem}")
    st.info("**先回答的科学问题：** " + p["question"])
    c1, c2, c3 = st.columns(3, gap="large")
    with c1:
        st.markdown("**第一层｜先定位和定量**")
        for x in p["first"]:
            st.markdown(f"- {x}")
    with c2:
        st.markdown("**第二层｜做机制判别**")
        for x in p["second"]:
            st.markdown(f"- {x}")
    with c3:
        st.markdown("**第三层｜需要时深挖**")
        for x in p["advanced"]:
            st.markdown(f"- {x}")
    st.markdown("**这类实验必须同步记录**")
    st.write(p["must"])
    st.warning("**科学边界：** " + p["boundary"])

    selected_names = p["first"] + p["second"] + p["advanced"]
    plan = _df()[_df()["name"].isin(selected_names)][
        ["category", "name", "instrument", "measure", "sample", "raw", "derived", "priority", "destructive"]
    ]
    with st.expander("展开查看对应仪器、样品和数据", expanded=False):
        st.dataframe(plan, hide_index=True, width="stretch", height=430)
        st.download_button(
            "下载该问题的测试路线 CSV",
            plan.to_csv(index=False).encode("utf-8-sig"),
            f"KDP_{problem}_测试路线.csv",
            "text/csv",
        )
    if st.button("保存这条测试路线到当前项目", type="primary", key="save_problem_route"):
        add_item(
            "experiment_plan",
            f"KDP测试路线｜{problem}",
            p["question"],
            {"problem": problem, "methods": plan.to_dict("records"), "must_record": p["must"]},
            "测试技术与仪器库",
            "待执行",
        )
        st.success("已保存到当前研究项目。")


def _method_library():
    st.markdown("### 测试技术与仪器库")
    st.caption("按类别筛选；每一种技术都说明‘测什么、用什么设备、样品怎么准备、原始数据保存什么、最后得到什么’。")
    cat = st.selectbox("测试类别", ["全部"] + CATEGORY_ORDER, key="testing_category")
    keyword = st.text_input("搜索技术/数据/问题", placeholder="例如：白纹、位错、热膨胀、Raman、LIDT、开裂")
    df = _df().copy()
    if cat != "全部":
        df = df[df["category"] == cat]
    if keyword.strip():
        q = keyword.strip().lower()
        search_cols = ["category", "name", "instrument", "measure", "use", "note"]
        mask = df[search_cols].astype(str).agg(" ".join, axis=1).str.lower().str.contains(q, regex=False)
        df = df[mask]
    st.caption(f"当前显示 {len(df)} 项技术")
    for idx, row in df.iterrows():
        with st.expander(f"{row['name']}  ｜  {row['priority']}", expanded=False):
            c1, c2 = st.columns(2, gap="large")
            with c1:
                st.markdown("**主要测什么**")
                st.write(row["measure"])
                st.markdown("**设备/平台**")
                st.write(row["instrument"])
                st.markdown("**样品怎么准备**")
                st.write(row["sample"])
            with c2:
                st.markdown("**必须保存的原始数据**")
                st.write(row["raw"])
                st.markdown("**最终得到的数据**")
                st.write(row["derived"])
                st.markdown("**在KDP课题里用来做什么**")
                st.write(row["use"])
            st.caption(f"破坏性：{row['destructive']}　｜　注意：{row['note']}")


def _matrix():
    st.markdown("### 全部测试技术—仪器—数据矩阵")
    st.caption("这张表适合做课题组测试资源盘点：哪些所内能做，哪些要外送，哪些还缺。")
    df = _df()[
        ["category", "name", "instrument", "measure", "sample", "raw", "derived", "use", "priority", "destructive"]
    ].copy()
    st.dataframe(df, hide_index=True, width="stretch", height=610)
    st.download_button(
        "下载完整测试技术矩阵 CSV",
        df.to_csv(index=False).encode("utf-8-sig"),
        "KDP_测试技术_仪器_数据矩阵.csv",
        "text/csv",
    )


def _plan_builder():
    st.markdown("### 生成自己的测试与表征计划")
    problems = st.multiselect(
        "当前要解决的问题",
        list(PROBLEM_WORKFLOWS),
        default=["肉眼大量白纹", "串丝 / 发丝状包裹体", "小晶体到大晶体尺度效应"],
    )
    base = []
    for p in problems:
        wf = PROBLEM_WORKFLOWS[p]
        base.extend(wf["first"] + wf["second"])
    base = list(dict.fromkeys(base))
    all_names = [m["name"] for m in METHODS]
    chosen = st.multiselect("计划采用的技术", all_names, default=[x for x in base if x in all_names])
    stage = st.selectbox("计划阶段", ["近期优先（1–4周）", "中期补充（1–3个月）", "完整研究方案"])
    location = st.text_input("测试平台/单位（可先留空）", placeholder="例如：所内公共技术中心 / 某高校测试中心")
    rows = []
    lookup = {m["name"]: m for m in METHODS}
    for name in chosen:
        m = lookup[name]
        rows.append(
            {
                "研究问题": "；".join(problems),
                "类别": m["category"],
                "技术": name,
                "设备/平台": m["instrument"],
                "样品要求": m["sample"],
                "必须保存原始数据": m["raw"],
                "最终数据": m["derived"],
                "优先级": m["priority"],
                "破坏性": m["destructive"],
                "计划阶段": stage,
                "拟测试单位": location,
                "状态": "待联系",
            }
        )
    plan = pd.DataFrame(rows)
    if plan.empty:
        st.info("先选择至少一种测试技术。")
        return
    edited = st.data_editor(plan, hide_index=True, width="stretch", height=500, num_rows="dynamic")
    st.download_button(
        "下载测试计划 CSV",
        edited.to_csv(index=False).encode("utf-8-sig"),
        "KDP_测试与表征计划.csv",
        "text/csv",
    )
    if st.button("保存测试与表征计划到当前项目", type="primary", key="save_testing_plan"):
        add_item(
            "experiment_plan",
            "KDP测试与表征计划",
            "；".join(problems),
            {"rows": edited.to_dict("records")},
            "测试技术与仪器库",
            "待执行",
        )
        st.success("已保存到当前研究项目。")


def _sample_rules():
    st.markdown("### KDP测试前的统一样品与数据规范")
    st.write("这部分很重要：如果方向、取样位置和生长历史没有记录，再高级的仪器数据也很难用于解释大尺寸缺陷。")
    st.dataframe(
        pd.DataFrame(
            [
                ["样品身份", "批次号、晶体号、母液批次、取样日期"],
                ["空间位置", "距籽晶距离、晶面/生长扇区、中心/边缘、白纹/串丝/正常区"],
                ["晶体学", "样品表面(hkl)、测试/热流/载荷方向[uvw]，必要时裂纹面+扩展方向"],
                ["尺寸阶段", "取样时对应小/中/大尺寸阶段，最好反推到生长时间"],
                ["表面与环境", "切割/抛光方式、表面粗糙度、清洁方式、保存湿度/温度"],
                ["原始数据", "原始曲线、图像、视频、仪器导出文件必须保留，不只保存最终Excel数字"],
                ["重复与不确定度", "重复样数量、均值/标准差、异常值处理、设备标定"],
                ["数据关联", "每个结果都能回到对应实验批次、缺陷照片、生长日志和计算任务"],
            ],
            columns=["必须记录", "内容"],
        ),
        hide_index=True,
        width="stretch",
    )
    st.warning("KDP水溶性且表面对环境敏感。样品加工、清洗与保存方案要避免水接触，并在测试记录中保留环境/表面状态；破坏性测试前先完成宏观缺陷摄影和空间编号。")


def testing_techniques_page():
    page_header(
        "KDP测试技术与仪器库",
        "从研究问题反推测试：白纹、串丝、尺度效应、杂质、光学质量和开裂分别应该用什么技术、找什么仪器、准备什么样品、保存什么数据。",
        "KDP CHARACTERIZATION & TESTING",
    )

    mode = st.radio(
        "你现在想做什么？",
        ["先看完整体系", "按问题找测试", "查一种仪器/技术", "查看全部矩阵", "生成测试计划", "样品与数据规范"],
        horizontal=True,
        key="testing_mode",
    )
    st.divider()
    if mode == "先看完整体系":
        _overview()
    elif mode == "按问题找测试":
        _problem_route()
    elif mode == "查一种仪器/技术":
        _method_library()
    elif mode == "查看全部矩阵":
        _matrix()
    elif mode == "生成测试计划":
        _plan_builder()
    else:
        _sample_rules()

    st.divider()
    section_title("和其他模块怎么配合", "测试技术库负责‘怎么测’，物性页负责‘模型参数怎么得到’")
    c1, c2, c3 = st.columns(3, gap="medium")
    with c1:
        _page_link("properties", "进入：物性参数与测试", ":material/biotech:")
    with c2:
        _page_link("experiment_log", "进入：实验记录与数据积累", ":material/database:")
    with c3:
        _page_link("theory", "进入：理论计算规划与分析", ":material/science:")
