# 建立case
# 初始修改

import pandapower as pd
import numpy as np


def LoadCase(path):
    # path 修改好算例的case路径
    net = pd.converter.from_mpc(r'path', f_hz=50, casename_mpc_file='caset')
    return net


def ModifyCase(net):
    # 输入网络结构net
    # 风机位置 16 18 节点 index [5,6]
    # 加入直流部分
    net.load['controllable'] = True
    pd.replace_ext_grid_by_gen(net)
    pd.replace_sgen_by_gen(net)
    net.gen.loc[0, 'slack'] = True
    pd.create_bus(net,
                  vn_kv=230,
                  name='DCnode',
                  index=24,
                  max_vm_pu=1.05,
                  min_vm_pu=0.95)
    pd.create_ext_grid(net,
                       bus=24,
                       max_q_mvar=500,
                       min_q_mvar=0,
                       min_p_mw=0,
                       max_p_mw=1000,
                       slack=False)
    pd.create_poly_cost(net,
                        element=0,
                        et='gen',
                        cp0_eur=0,
                        cp1_eur_per_mw=0,
                        cp2_eur_per_mw2=0)
    pd.create_dcline(net,
                     from_bus=24,
                     to_bus=17,
                     p_mw=400,
                     loss_mw=10,
                     loss_percent=5,
                     vm_from_pu=1.05,
                     vm_to_pu=0.95,
                     name='DC1',
                     max_p_mw=1000,
                     max_q_from_mvar=500,
                     min_q_from_mvar=-500,
                     max_q_to_mvar=500,
                     min_q_to_mvar=-500)
    return net


def StateOfGen(net, Param_Relia, R):
    # 机组运行可靠性
    # Param_Relia numpy n x 2
    # don't include dc gen
    for i in range(len(R)):
        if R[i] < Param_Relia[i, 0]:
            net.gen.loc[i, 'in_service'] = False
    # 找到slack机组
    if net.gen.loc[0, 'in_service'] is True:
        return net
    else:
        x = np.array(np.where(net.gen.loc[:, 'slack'] is False))
        s = x[0, 0]
        net.gen.loc[s, 'slack'] = True
        return net


def WindPower(net, WP, wind):
    # 修改风机的出力参数
    P = np.zeros([1, len(WP)])
    Vin = 3
    Vr = 13.5
    Vout = 20
    for i in range(len(WP)):
        if (WP <= Vin) | (WP > Vout):
            P[0, i] = 0
        elif (WP > Vin) & (WP <= Vr):
            P[0, i] = wind / (Vr-Vin) * WP - Vin*150/(Vr-Vin)
        elif (WP > Vr) & (WP <= Vout):
            P[0, i] = wind
    net.gen.loc[5, 'max_p_mw'] = P[0, 0]
    net.gen.loc[6, 'max_p_mw'] = P[0, 1]
    net.gen.loc[5, 'min_p_mw'] = 0
    net.gen.loc[6, 'min_p_mw'] = 0
    net.gen.loc[5, 'max_q_mvar'] = P[0, 0]
    net.gen.loc[6, 'max_q_mvar'] = P[0, 1]
    net.gen.loc[5, 'min_q_mvar'] = 0
    net.gen.loc[6, 'min_q_mvar'] = 0
    return net


def StateOfDC(net, Param_Relia, R, DCPOWER):
    # 直流系统的可靠性
    # 直流 400/8000
    if R <= Param_Relia[0, 0]:
        net.dcline.loc[0, 'in_service'] = False
    elif R > Param_Relia[0, 0] & R <= Param_Relia[0, 1]:
        net.dcline.loc[0, 'max_p_mw'] = DCPOWER*0.2
        net.dcline.loc[0, 'max_q_from_mvar'] = DCPOWER*0.2
        net.dcline.loc[0, 'min_q_from_mvar'] = -DCPOWER*0.2
        net.dcline.loc[0, 'max_q_to_mvar'] = DCPOWER*0.2
        net.dcline.loc[0, 'min_q_to_mvar'] = -DCPOWER*0.2
    elif R > Param_Relia[0, 1] & R <= Param_Relia[0, 2]:
        net.dcline.loc[0, 'max_p_mw'] = DCPOWER*0.5
        net.dcline.loc[0, 'max_q_from_mvar'] = DCPOWER*0.5
        net.dcline.loc[0, 'min_q_from_mvar'] = -DCPOWER*0.5
        net.dcline.loc[0, 'max_q_to_mvar'] = DCPOWER*0.5
        net.dcline.loc[0, 'min_q_to_mvar'] = -DCPOWER*0.5
    else:
        net.dcline.loc[0, 'max_p_mw'] = DCPOWER
        net.dcline.loc[0, 'max_q_from_mvar'] = DCPOWER
        net.dcline.loc[0, 'min_q_from_mvar'] = -DCPOWER
        net.dcline.loc[0, 'max_q_to_mvar'] = DCPOWER
        net.dcline.loc[0, 'min_q_to_mvar'] = -DCPOWER
    return net


if __name__ == "__main__":
    pass
