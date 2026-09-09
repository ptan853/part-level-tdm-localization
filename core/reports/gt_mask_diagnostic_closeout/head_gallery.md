# 头部编辑：28 个案例

**固定布局：左列自动 mask，右列 GT mask；三行分别为 Endpoint N=7、RK2 N=7、RK2 N=15。**

每例包含原图、实际控制 mask、原始与目标描述，以及单一评分者的编辑/保存评分（0–2）。编辑 1 分只代表部分成功。

本图集完整展示所有头部案例，不按结果筛选。动物头部 18 例，人形主体头部 10 例；后者包括人、机器人与外星人。

<a id="head-index"></a>
## 案例索引

### 动物头部（18 例）

- [synth_0028：cow → dragon head](#synth_0028)
- [synth_0029：dog → lion head](#synth_0029)
- [synth_0030：bear → dog head](#synth_0030)
- [synth_0031：horse → dragon head](#synth_0031)
- [synth_0032：cat → dragon head](#synth_0032)
- [synth_0033：dog → cat head](#synth_0033)
- [synth_0034：dog → unicorn head](#synth_0034)
- [synth_0035：cat → cheetah head](#synth_0035)
- [synth_0036：bear → lion head](#synth_0036)
- [synth_0037：dog → dragon head](#synth_0037)
- [synth_0038：horse → dragon head](#synth_0038)
- [synth_0039：cow → unicorn head](#synth_0039)
- [synth_0040：bear → tiger head](#synth_0040)
- [synth_0041：cat → panda head](#synth_0041)
- [synth_0042：panda → cheetah head](#synth_0042)
- [synth_0043：bear → dragon head](#synth_0043)
- [synth_0044：bear → lion head](#synth_0044)
- [synth_0045：dog → panda head](#synth_0045)

### 人形主体头部（10 例）

- [synth_0000：alien → robot head](#synth_0000)
- [synth_0001：robot → bear head](#synth_0001)
- [synth_0002：robot → bear head](#synth_0002)
- [synth_0003：alien → robot head](#synth_0003)
- [synth_0004：robot → tattooed head](#synth_0004)
- [synth_0005：man → robot head](#synth_0005)
- [synth_0006：girl → robot head](#synth_0006)
- [synth_0007：alien → robot head](#synth_0007)
- [synth_0008：robot → alien head](#synth_0008)
- [synth_0009：alien → bear head](#synth_0009)

---

## 动物头部

<a id="synth_0028"></a>
## synth_0028：head → dragon

**原始描述：** A cow at a restaurant

**目标描述：** A cow with dragon head at a restaurant

**预期范围变化：** 基本不变

### 原图与控制区域

| 原始输入图片 | 自动 mask | GT mask |
| --- | --- | --- |
| ![Source](assets/f03ad80412830e796b16.png) | ![Automatic mask](assets/synth_0028_auto_control_mask.png) | ![GT control mask](assets/synth_0028_gt_control_mask.png) |

白色＝允许编辑，黑色＝受保护区域。两张 mask 均为运行配置指定的实际输入，未平滑或额外扩张。

### 生成结果：固定左右列

| 控制方法与时长 | 使用自动 mask | 使用 GT mask |
| --- | --- | --- |
| **Endpoint · N=7**<br>每步更新完成后，约束 mask 外部；前 7 步启用 | ![endpoint_auto](assets/240d02991ef6196c5e72.jpg)<br>**编辑 0 / 保存 1** | ![endpoint_gt](assets/4f6c581fe60ae348f170.jpg)<br>**编辑 0 / 保存 1** |
| **RK2 · N=7**<br>中点和终点均受控；前 7 步启用 | ![rk2_auto](assets/c1b1764ea1f948674db2.jpg)<br>**编辑 0 / 保存 1** | ![rk2_gt](assets/b8c95e82052fc3e9d35c.jpg)<br>**编辑 0 / 保存 1** |
| **RK2 · N=15**<br>中点和终点均受控；全部 15 步启用 | ![rk2_n15_auto](assets/6c24bc5287dab452a628.jpg)<br>**编辑 0 / 保存 2** | ![rk2_n15_gt](assets/149354082fbfeda17287.jpg)<br>**编辑 0 / 保存 2** |

[返回头部案例索引](#head-index)


---

<a id="synth_0029"></a>
## synth_0029：head → lion

**原始描述：** A dog at a pool

**目标描述：** A dog with lion head at a pool

**预期范围变化：** 扩张

### 原图与控制区域

| 原始输入图片 | 自动 mask | GT mask |
| --- | --- | --- |
| ![Source](assets/2afbd90e6bc55f79c1d6.png) | ![Automatic mask](assets/synth_0029_auto_control_mask.png) | ![GT control mask](assets/synth_0029_gt_control_mask.png) |

白色＝允许编辑，黑色＝受保护区域。两张 mask 均为运行配置指定的实际输入，未平滑或额外扩张。

### 生成结果：固定左右列

| 控制方法与时长 | 使用自动 mask | 使用 GT mask |
| --- | --- | --- |
| **Endpoint · N=7**<br>每步更新完成后，约束 mask 外部；前 7 步启用 | ![endpoint_auto](assets/9888ab9ccab6ffd74171.jpg)<br>**编辑 1 / 保存 1** | ![endpoint_gt](assets/5a3d20215ba3d703632f.jpg)<br>**编辑 0 / 保存 2** |
| **RK2 · N=7**<br>中点和终点均受控；前 7 步启用 | ![rk2_auto](assets/25011f7d449388bb7543.jpg)<br>**编辑 1 / 保存 1** | ![rk2_gt](assets/462a79e6fb00434f748a.jpg)<br>**编辑 0 / 保存 2** |
| **RK2 · N=15**<br>中点和终点均受控；全部 15 步启用 | ![rk2_n15_auto](assets/ff6e41859dd958541496.jpg)<br>**编辑 0 / 保存 1** | ![rk2_n15_gt](assets/5f1e10596ce96ed2e128.jpg)<br>**编辑 0 / 保存 2** |

[返回头部案例索引](#head-index)


---

<a id="synth_0030"></a>
## synth_0030：head → dog

**原始描述：** A bear at a jungle

**目标描述：** A bear with dog head at a jungle

**预期范围变化：** 收缩

### 原图与控制区域

| 原始输入图片 | 自动 mask | GT mask |
| --- | --- | --- |
| ![Source](assets/6bb11c4ef06e71199ce0.png) | ![Automatic mask](assets/synth_0030_auto_control_mask.png) | ![GT control mask](assets/synth_0030_gt_control_mask.png) |

白色＝允许编辑，黑色＝受保护区域。两张 mask 均为运行配置指定的实际输入，未平滑或额外扩张。

### 生成结果：固定左右列

| 控制方法与时长 | 使用自动 mask | 使用 GT mask |
| --- | --- | --- |
| **Endpoint · N=7**<br>每步更新完成后，约束 mask 外部；前 7 步启用 | ![endpoint_auto](assets/fdcc88464fdc7727bb87.jpg)<br>**编辑 0 / 保存 2** | ![endpoint_gt](assets/57bdcf133ee2894cafb8.jpg)<br>**编辑 0 / 保存 2** |
| **RK2 · N=7**<br>中点和终点均受控；前 7 步启用 | ![rk2_auto](assets/b6f6c8ea983450715f8e.jpg)<br>**编辑 2 / 保存 2** | ![rk2_gt](assets/8912960e3eeb49755483.jpg)<br>**编辑 0 / 保存 1** |
| **RK2 · N=15**<br>中点和终点均受控；全部 15 步启用 | ![rk2_n15_auto](assets/698f7d4e8352b9328aa1.jpg)<br>**编辑 0 / 保存 2** | ![rk2_n15_gt](assets/c610440aea2852e78830.jpg)<br>**编辑 0 / 保存 2** |

[返回头部案例索引](#head-index)


---

<a id="synth_0031"></a>
## synth_0031：head → dragon

**原始描述：** A horse at a jungle

**目标描述：** A horse with dragon head at a jungle

**预期范围变化：** 扩张

### 原图与控制区域

| 原始输入图片 | 自动 mask | GT mask |
| --- | --- | --- |
| ![Source](assets/79bb0a97fc8b87de1aa9.png) | ![Automatic mask](assets/synth_0031_auto_control_mask.png) | ![GT control mask](assets/synth_0031_gt_control_mask.png) |

白色＝允许编辑，黑色＝受保护区域。两张 mask 均为运行配置指定的实际输入，未平滑或额外扩张。

### 生成结果：固定左右列

| 控制方法与时长 | 使用自动 mask | 使用 GT mask |
| --- | --- | --- |
| **Endpoint · N=7**<br>每步更新完成后，约束 mask 外部；前 7 步启用 | ![endpoint_auto](assets/8db3e31382320ca68de8.jpg)<br>**编辑 0 / 保存 1** | ![endpoint_gt](assets/5184bee927e1e89c48ee.jpg)<br>**编辑 0 / 保存 1** |
| **RK2 · N=7**<br>中点和终点均受控；前 7 步启用 | ![rk2_auto](assets/0f105094eac83f0e768e.jpg)<br>**编辑 0 / 保存 1** | ![rk2_gt](assets/87cdf2bec6205e53347f.jpg)<br>**编辑 0 / 保存 2** |
| **RK2 · N=15**<br>中点和终点均受控；全部 15 步启用 | ![rk2_n15_auto](assets/ff5b787137cde335b30b.jpg)<br>**编辑 0 / 保存 2** | ![rk2_n15_gt](assets/39446eaec433dc2473ac.jpg)<br>**编辑 0 / 保存 2** |

[返回头部案例索引](#head-index)


---

<a id="synth_0032"></a>
## synth_0032：head → dragon

**原始描述：** A cat at a desert

**目标描述：** A cat with dragon head at a desert

**预期范围变化：** 扩张

### 原图与控制区域

| 原始输入图片 | 自动 mask | GT mask |
| --- | --- | --- |
| ![Source](assets/5e879b4944443b6f90e2.png) | ![Automatic mask](assets/synth_0032_auto_control_mask.png) | ![GT control mask](assets/synth_0032_gt_control_mask.png) |

白色＝允许编辑，黑色＝受保护区域。两张 mask 均为运行配置指定的实际输入，未平滑或额外扩张。

### 生成结果：固定左右列

| 控制方法与时长 | 使用自动 mask | 使用 GT mask |
| --- | --- | --- |
| **Endpoint · N=7**<br>每步更新完成后，约束 mask 外部；前 7 步启用 | ![endpoint_auto](assets/9dc39099c07a2e91e915.jpg)<br>**编辑 0 / 保存 2** | ![endpoint_gt](assets/963d3fa6da3a2940c07d.jpg)<br>**编辑 0 / 保存 2** |
| **RK2 · N=7**<br>中点和终点均受控；前 7 步启用 | ![rk2_auto](assets/d1ad2aa96989835982a4.jpg)<br>**编辑 0 / 保存 2** | ![rk2_gt](assets/11e9fb0017f20c673c31.jpg)<br>**编辑 0 / 保存 2** |
| **RK2 · N=15**<br>中点和终点均受控；全部 15 步启用 | ![rk2_n15_auto](assets/2bcd5a8484feb59ddb45.jpg)<br>**编辑 0 / 保存 2** | ![rk2_n15_gt](assets/800d32e7a2f565179556.jpg)<br>**编辑 0 / 保存 2** |

[返回头部案例索引](#head-index)


---

<a id="synth_0033"></a>
## synth_0033：head → cat

**原始描述：** A dog at a restaurant

**目标描述：** A dog with cat head at a restaurant

**预期范围变化：** 基本不变

### 原图与控制区域

| 原始输入图片 | 自动 mask | GT mask |
| --- | --- | --- |
| ![Source](assets/8bdc74a36ac254d6ecfe.png) | ![Automatic mask](assets/synth_0033_auto_control_mask.png) | ![GT control mask](assets/synth_0033_gt_control_mask.png) |

白色＝允许编辑，黑色＝受保护区域。两张 mask 均为运行配置指定的实际输入，未平滑或额外扩张。

### 生成结果：固定左右列

| 控制方法与时长 | 使用自动 mask | 使用 GT mask |
| --- | --- | --- |
| **Endpoint · N=7**<br>每步更新完成后，约束 mask 外部；前 7 步启用 | ![endpoint_auto](assets/b2bcaf98036c2ca1326a.jpg)<br>**编辑 0 / 保存 0** | ![endpoint_gt](assets/a4fc1dd9a75327d37461.jpg)<br>**编辑 0 / 保存 2** |
| **RK2 · N=7**<br>中点和终点均受控；前 7 步启用 | ![rk2_auto](assets/e7d5f7de6613ab27f55f.jpg)<br>**编辑 0 / 保存 0** | ![rk2_gt](assets/3a11580756824cb15fbb.jpg)<br>**编辑 0 / 保存 2** |
| **RK2 · N=15**<br>中点和终点均受控；全部 15 步启用 | ![rk2_n15_auto](assets/497ed4868e70254a4eda.jpg)<br>**编辑 0 / 保存 0** | ![rk2_n15_gt](assets/d3baf78859f0df9439ef.jpg)<br>**编辑 0 / 保存 2** |

[返回头部案例索引](#head-index)


---

<a id="synth_0034"></a>
## synth_0034：head → unicorn

**原始描述：** A dog at a mountain

**目标描述：** A dog with unicorn head at a mountain

**预期范围变化：** 扩张

### 原图与控制区域

| 原始输入图片 | 自动 mask | GT mask |
| --- | --- | --- |
| ![Source](assets/38588b85486a01cd4341.png) | ![Automatic mask](assets/synth_0034_auto_control_mask.png) | ![GT control mask](assets/synth_0034_gt_control_mask.png) |

白色＝允许编辑，黑色＝受保护区域。两张 mask 均为运行配置指定的实际输入，未平滑或额外扩张。

### 生成结果：固定左右列

| 控制方法与时长 | 使用自动 mask | 使用 GT mask |
| --- | --- | --- |
| **Endpoint · N=7**<br>每步更新完成后，约束 mask 外部；前 7 步启用 | ![endpoint_auto](assets/71ed3858eb60ddc7f54c.jpg)<br>**编辑 0 / 保存 2** | ![endpoint_gt](assets/460e187cf9fe57619464.jpg)<br>**编辑 0 / 保存 2** |
| **RK2 · N=7**<br>中点和终点均受控；前 7 步启用 | ![rk2_auto](assets/9828cefe9481f845fa9b.jpg)<br>**编辑 0 / 保存 2** | ![rk2_gt](assets/7788e7d84535019af8be.jpg)<br>**编辑 0 / 保存 2** |
| **RK2 · N=15**<br>中点和终点均受控；全部 15 步启用 | ![rk2_n15_auto](assets/3c64ed88418f46653ec2.jpg)<br>**编辑 0 / 保存 2** | ![rk2_n15_gt](assets/1d5d7a6da5220cb12def.jpg)<br>**编辑 0 / 保存 2** |

[返回头部案例索引](#head-index)


---

<a id="synth_0035"></a>
## synth_0035：head → cheetah

**原始描述：** A cat at a museum

**目标描述：** A cat with cheetah head at a museum

**预期范围变化：** 扩张

### 原图与控制区域

| 原始输入图片 | 自动 mask | GT mask |
| --- | --- | --- |
| ![Source](assets/1e81c9d2670376c801ef.png) | ![Automatic mask](assets/synth_0035_auto_control_mask.png) | ![GT control mask](assets/synth_0035_gt_control_mask.png) |

白色＝允许编辑，黑色＝受保护区域。两张 mask 均为运行配置指定的实际输入，未平滑或额外扩张。

### 生成结果：固定左右列

| 控制方法与时长 | 使用自动 mask | 使用 GT mask |
| --- | --- | --- |
| **Endpoint · N=7**<br>每步更新完成后，约束 mask 外部；前 7 步启用 | ![endpoint_auto](assets/e3707d893f25b30a5d0f.jpg)<br>**编辑 1 / 保存 1** | ![endpoint_gt](assets/f92b785fd4e36a7fe9a1.jpg)<br>**编辑 1 / 保存 2** |
| **RK2 · N=7**<br>中点和终点均受控；前 7 步启用 | ![rk2_auto](assets/1bbce23108f4def97e19.jpg)<br>**编辑 1 / 保存 1** | ![rk2_gt](assets/9138bf88c0b1233c4005.jpg)<br>**编辑 0 / 保存 2** |
| **RK2 · N=15**<br>中点和终点均受控；全部 15 步启用 | ![rk2_n15_auto](assets/54cf113c136ee4aec034.jpg)<br>**编辑 1 / 保存 2** | ![rk2_n15_gt](assets/acee1727ff4b558ef0b4.jpg)<br>**编辑 0 / 保存 2** |

[返回头部案例索引](#head-index)


---

<a id="synth_0036"></a>
## synth_0036：head → lion

**原始描述：** A bear at a zoo

**目标描述：** A bear with lion head at a zoo

**预期范围变化：** 基本不变

### 原图与控制区域

| 原始输入图片 | 自动 mask | GT mask |
| --- | --- | --- |
| ![Source](assets/84cfd41d06ab1f79d1f7.png) | ![Automatic mask](assets/synth_0036_auto_control_mask.png) | ![GT control mask](assets/synth_0036_gt_control_mask.png) |

白色＝允许编辑，黑色＝受保护区域。两张 mask 均为运行配置指定的实际输入，未平滑或额外扩张。

### 生成结果：固定左右列

| 控制方法与时长 | 使用自动 mask | 使用 GT mask |
| --- | --- | --- |
| **Endpoint · N=7**<br>每步更新完成后，约束 mask 外部；前 7 步启用 | ![endpoint_auto](assets/6e2c1d1496fe1e105425.jpg)<br>**编辑 0 / 保存 2** | ![endpoint_gt](assets/f5e55a28da286b5e65b6.jpg)<br>**编辑 1 / 保存 2** |
| **RK2 · N=7**<br>中点和终点均受控；前 7 步启用 | ![rk2_auto](assets/c042230afcff88056867.jpg)<br>**编辑 0 / 保存 2** | ![rk2_gt](assets/7369ca3b2c5dde87a1c4.jpg)<br>**编辑 1 / 保存 2** |
| **RK2 · N=15**<br>中点和终点均受控；全部 15 步启用 | ![rk2_n15_auto](assets/b20fad5076e2dc72f7ad.jpg)<br>**编辑 0 / 保存 2** | ![rk2_n15_gt](assets/b4d9dd8c117f02b8544c.jpg)<br>**编辑 0 / 保存 2** |

[返回头部案例索引](#head-index)


---

<a id="synth_0037"></a>
## synth_0037：head → dragon

**原始描述：** A dog at a farm

**目标描述：** A dog with dragon head at a farm

**预期范围变化：** 扩张

### 原图与控制区域

| 原始输入图片 | 自动 mask | GT mask |
| --- | --- | --- |
| ![Source](assets/5a474704adb33121c37c.png) | ![Automatic mask](assets/synth_0037_auto_control_mask.png) | ![GT control mask](assets/synth_0037_gt_control_mask.png) |

白色＝允许编辑，黑色＝受保护区域。两张 mask 均为运行配置指定的实际输入，未平滑或额外扩张。

### 生成结果：固定左右列

| 控制方法与时长 | 使用自动 mask | 使用 GT mask |
| --- | --- | --- |
| **Endpoint · N=7**<br>每步更新完成后，约束 mask 外部；前 7 步启用 | ![endpoint_auto](assets/18e4c738fc55d0ba5566.jpg)<br>**编辑 0 / 保存 1** | ![endpoint_gt](assets/4763602244900de37980.jpg)<br>**编辑 0 / 保存 2** |
| **RK2 · N=7**<br>中点和终点均受控；前 7 步启用 | ![rk2_auto](assets/26e4cc7679a7e55d18e3.jpg)<br>**编辑 0 / 保存 2** | ![rk2_gt](assets/adacc66f1f38a8498a52.jpg)<br>**编辑 0 / 保存 2** |
| **RK2 · N=15**<br>中点和终点均受控；全部 15 步启用 | ![rk2_n15_auto](assets/3102e845a99f1701d9b1.jpg)<br>**编辑 0 / 保存 2** | ![rk2_n15_gt](assets/76369484472bbf839d63.jpg)<br>**编辑 0 / 保存 2** |

[返回头部案例索引](#head-index)


---

<a id="synth_0038"></a>
## synth_0038：head → dragon

**原始描述：** A horse at a zoo

**目标描述：** A horse with dragon head at a zoo

**预期范围变化：** 扩张

### 原图与控制区域

| 原始输入图片 | 自动 mask | GT mask |
| --- | --- | --- |
| ![Source](assets/e419c6b72ce0606df766.png) | ![Automatic mask](assets/synth_0038_auto_control_mask.png) | ![GT control mask](assets/synth_0038_gt_control_mask.png) |

白色＝允许编辑，黑色＝受保护区域。两张 mask 均为运行配置指定的实际输入，未平滑或额外扩张。

### 生成结果：固定左右列

| 控制方法与时长 | 使用自动 mask | 使用 GT mask |
| --- | --- | --- |
| **Endpoint · N=7**<br>每步更新完成后，约束 mask 外部；前 7 步启用 | ![endpoint_auto](assets/c3693eb7f8b9efedece2.jpg)<br>**编辑 0 / 保存 2** | ![endpoint_gt](assets/ae49daa7326965d2a7fc.jpg)<br>**编辑 0 / 保存 2** |
| **RK2 · N=7**<br>中点和终点均受控；前 7 步启用 | ![rk2_auto](assets/904b87710d0cf7f921d9.jpg)<br>**编辑 0 / 保存 2** | ![rk2_gt](assets/b6c5ef78731f2899191d.jpg)<br>**编辑 0 / 保存 2** |
| **RK2 · N=15**<br>中点和终点均受控；全部 15 步启用 | ![rk2_n15_auto](assets/8c73904290ab21a425df.jpg)<br>**编辑 0 / 保存 1** | ![rk2_n15_gt](assets/3dda1671b03999e049e4.jpg)<br>**编辑 0 / 保存 2** |

[返回头部案例索引](#head-index)


---

<a id="synth_0039"></a>
## synth_0039：head → unicorn

**原始描述：** A cow at a house

**目标描述：** A cow with unicorn head at a house

**预期范围变化：** 扩张

### 原图与控制区域

| 原始输入图片 | 自动 mask | GT mask |
| --- | --- | --- |
| ![Source](assets/c7ba2274dc2cdc72072b.png) | ![Automatic mask](assets/synth_0039_auto_control_mask.png) | ![GT control mask](assets/synth_0039_gt_control_mask.png) |

白色＝允许编辑，黑色＝受保护区域。两张 mask 均为运行配置指定的实际输入，未平滑或额外扩张。

### 生成结果：固定左右列

| 控制方法与时长 | 使用自动 mask | 使用 GT mask |
| --- | --- | --- |
| **Endpoint · N=7**<br>每步更新完成后，约束 mask 外部；前 7 步启用 | ![endpoint_auto](assets/10d9c6bfb8b584e630d3.jpg)<br>**编辑 2 / 保存 1** | ![endpoint_gt](assets/64a93acd311ac04f851c.jpg)<br>**编辑 0 / 保存 1** |
| **RK2 · N=7**<br>中点和终点均受控；前 7 步启用 | ![rk2_auto](assets/50e768d2d5d59408b052.jpg)<br>**编辑 2 / 保存 1** | ![rk2_gt](assets/488fe1810fc2d692a311.jpg)<br>**编辑 0 / 保存 1** |
| **RK2 · N=15**<br>中点和终点均受控；全部 15 步启用 | ![rk2_n15_auto](assets/6a22659fd4e9d6ce7867.jpg)<br>**编辑 2 / 保存 1** | ![rk2_n15_gt](assets/aa24b77f5878946cf95e.jpg)<br>**编辑 0 / 保存 2** |

[返回头部案例索引](#head-index)


---

<a id="synth_0040"></a>
## synth_0040：head → tiger

**原始描述：** A bear at a pool

**目标描述：** A bear with tiger head at a pool

**预期范围变化：** 基本不变

### 原图与控制区域

| 原始输入图片 | 自动 mask | GT mask |
| --- | --- | --- |
| ![Source](assets/7e45e2bca6994441434e.png) | ![Automatic mask](assets/synth_0040_auto_control_mask.png) | ![GT control mask](assets/synth_0040_gt_control_mask.png) |

白色＝允许编辑，黑色＝受保护区域。两张 mask 均为运行配置指定的实际输入，未平滑或额外扩张。

### 生成结果：固定左右列

| 控制方法与时长 | 使用自动 mask | 使用 GT mask |
| --- | --- | --- |
| **Endpoint · N=7**<br>每步更新完成后，约束 mask 外部；前 7 步启用 | ![endpoint_auto](assets/0bef0cb252bed1cb2e26.jpg)<br>**编辑 1 / 保存 1** | ![endpoint_gt](assets/b14bad135e62fb0c2f5b.jpg)<br>**编辑 1 / 保存 2** |
| **RK2 · N=7**<br>中点和终点均受控；前 7 步启用 | ![rk2_auto](assets/0a09ee94400962a19bfd.jpg)<br>**编辑 1 / 保存 1** | ![rk2_gt](assets/5cbadadafa883ee66287.jpg)<br>**编辑 1 / 保存 1** |
| **RK2 · N=15**<br>中点和终点均受控；全部 15 步启用 | ![rk2_n15_auto](assets/ebcc8612f6874978d223.jpg)<br>**编辑 1 / 保存 2** | ![rk2_n15_gt](assets/846a199f1e04afb7b61e.jpg)<br>**编辑 1 / 保存 2** |

[返回头部案例索引](#head-index)


---

<a id="synth_0041"></a>
## synth_0041：head → panda

**原始描述：** A cat at a mountain

**目标描述：** A cat with panda head at a mountain

**预期范围变化：** 扩张

### 原图与控制区域

| 原始输入图片 | 自动 mask | GT mask |
| --- | --- | --- |
| ![Source](assets/90b04250be827c4146cc.png) | ![Automatic mask](assets/synth_0041_auto_control_mask.png) | ![GT control mask](assets/synth_0041_gt_control_mask.png) |

白色＝允许编辑，黑色＝受保护区域。两张 mask 均为运行配置指定的实际输入，未平滑或额外扩张。

### 生成结果：固定左右列

| 控制方法与时长 | 使用自动 mask | 使用 GT mask |
| --- | --- | --- |
| **Endpoint · N=7**<br>每步更新完成后，约束 mask 外部；前 7 步启用 | ![endpoint_auto](assets/d461c6dac760eb91d000.jpg)<br>**编辑 1 / 保存 2** | ![endpoint_gt](assets/082fb33492ce60987196.jpg)<br>**编辑 1 / 保存 2** |
| **RK2 · N=7**<br>中点和终点均受控；前 7 步启用 | ![rk2_auto](assets/55662122a7a4e9f150f8.jpg)<br>**编辑 1 / 保存 2** | ![rk2_gt](assets/047e4b013384b0904c87.jpg)<br>**编辑 1 / 保存 2** |
| **RK2 · N=15**<br>中点和终点均受控；全部 15 步启用 | ![rk2_n15_auto](assets/7c4ada8e69271135c2e4.jpg)<br>**编辑 1 / 保存 2** | ![rk2_n15_gt](assets/284dbf72a9f96f577eac.jpg)<br>**编辑 1 / 保存 2** |

[返回头部案例索引](#head-index)


---

<a id="synth_0042"></a>
## synth_0042：head → cheetah

**原始描述：** A panda at a school

**目标描述：** A panda with cheetah head at a school

**预期范围变化：** 基本不变

### 原图与控制区域

| 原始输入图片 | 自动 mask | GT mask |
| --- | --- | --- |
| ![Source](assets/c7e3adc078073f20907a.png) | ![Automatic mask](assets/synth_0042_auto_control_mask.png) | ![GT control mask](assets/synth_0042_gt_control_mask.png) |

白色＝允许编辑，黑色＝受保护区域。两张 mask 均为运行配置指定的实际输入，未平滑或额外扩张。

### 生成结果：固定左右列

| 控制方法与时长 | 使用自动 mask | 使用 GT mask |
| --- | --- | --- |
| **Endpoint · N=7**<br>每步更新完成后，约束 mask 外部；前 7 步启用 | ![endpoint_auto](assets/415ceff2b7921278df37.jpg)<br>**编辑 0 / 保存 0** | ![endpoint_gt](assets/828c3c3e6274bbba5228.jpg)<br>**编辑 0 / 保存 2** |
| **RK2 · N=7**<br>中点和终点均受控；前 7 步启用 | ![rk2_auto](assets/d71de821f607ec6ad210.jpg)<br>**编辑 0 / 保存 1** | ![rk2_gt](assets/8190b83b7906494a72a6.jpg)<br>**编辑 0 / 保存 2** |
| **RK2 · N=15**<br>中点和终点均受控；全部 15 步启用 | ![rk2_n15_auto](assets/7ea017c63fbda9d560dd.jpg)<br>**编辑 0 / 保存 1** | ![rk2_n15_gt](assets/00d1f57c5b7ac1a2f5e0.jpg)<br>**编辑 0 / 保存 2** |

[返回头部案例索引](#head-index)


---

<a id="synth_0043"></a>
## synth_0043：head → dragon

**原始描述：** A bear at a jungle

**目标描述：** A bear with dragon head at a jungle

**预期范围变化：** 扩张

### 原图与控制区域

| 原始输入图片 | 自动 mask | GT mask |
| --- | --- | --- |
| ![Source](assets/8d5c80c059b7d1323f90.png) | ![Automatic mask](assets/synth_0043_auto_control_mask.png) | ![GT control mask](assets/synth_0043_gt_control_mask.png) |

白色＝允许编辑，黑色＝受保护区域。两张 mask 均为运行配置指定的实际输入，未平滑或额外扩张。

### 生成结果：固定左右列

| 控制方法与时长 | 使用自动 mask | 使用 GT mask |
| --- | --- | --- |
| **Endpoint · N=7**<br>每步更新完成后，约束 mask 外部；前 7 步启用 | ![endpoint_auto](assets/ed6316e1238dd999b20d.jpg)<br>**编辑 0 / 保存 1** | ![endpoint_gt](assets/a5c03bb835191dad6e42.jpg)<br>**编辑 0 / 保存 2** |
| **RK2 · N=7**<br>中点和终点均受控；前 7 步启用 | ![rk2_auto](assets/dd6bae6c42c28dd8ac51.jpg)<br>**编辑 0 / 保存 1** | ![rk2_gt](assets/03b01a7b5c24681bee3c.jpg)<br>**编辑 0 / 保存 1** |
| **RK2 · N=15**<br>中点和终点均受控；全部 15 步启用 | ![rk2_n15_auto](assets/3dda9f1a0fe8a4dd7fa0.jpg)<br>**编辑 0 / 保存 2** | ![rk2_n15_gt](assets/552a68735ac28f4aeee8.jpg)<br>**编辑 0 / 保存 2** |

[返回头部案例索引](#head-index)


---

<a id="synth_0044"></a>
## synth_0044：head → lion

**原始描述：** A bear at a zoo

**目标描述：** A bear with lion head at a zoo

**预期范围变化：** 基本不变

### 原图与控制区域

| 原始输入图片 | 自动 mask | GT mask |
| --- | --- | --- |
| ![Source](assets/8d09eb3014b83901a88f.png) | ![Automatic mask](assets/synth_0044_auto_control_mask.png) | ![GT control mask](assets/synth_0044_gt_control_mask.png) |

白色＝允许编辑，黑色＝受保护区域。两张 mask 均为运行配置指定的实际输入，未平滑或额外扩张。

### 生成结果：固定左右列

| 控制方法与时长 | 使用自动 mask | 使用 GT mask |
| --- | --- | --- |
| **Endpoint · N=7**<br>每步更新完成后，约束 mask 外部；前 7 步启用 | ![endpoint_auto](assets/1922087ddd1147b68583.jpg)<br>**编辑 0 / 保存 1** | ![endpoint_gt](assets/6e769a5bcb335368fabc.jpg)<br>**编辑 1 / 保存 2** |
| **RK2 · N=7**<br>中点和终点均受控；前 7 步启用 | ![rk2_auto](assets/08484a3354f6d7fecca9.jpg)<br>**编辑 0 / 保存 1** | ![rk2_gt](assets/a4429d7cd01dea4926f2.jpg)<br>**编辑 0 / 保存 1** |
| **RK2 · N=15**<br>中点和终点均受控；全部 15 步启用 | ![rk2_n15_auto](assets/5276f5708306ca21224c.jpg)<br>**编辑 0 / 保存 2** | ![rk2_n15_gt](assets/9f5cff316f09fa369ef8.jpg)<br>**编辑 0 / 保存 2** |

[返回头部案例索引](#head-index)


---

<a id="synth_0045"></a>
## synth_0045：head → panda

**原始描述：** A dog at a store

**目标描述：** A dog with panda head at a store

**预期范围变化：** 扩张

### 原图与控制区域

| 原始输入图片 | 自动 mask | GT mask |
| --- | --- | --- |
| ![Source](assets/f7b6833a7d2672aea5de.png) | ![Automatic mask](assets/synth_0045_auto_control_mask.png) | ![GT control mask](assets/synth_0045_gt_control_mask.png) |

白色＝允许编辑，黑色＝受保护区域。两张 mask 均为运行配置指定的实际输入，未平滑或额外扩张。

### 生成结果：固定左右列

| 控制方法与时长 | 使用自动 mask | 使用 GT mask |
| --- | --- | --- |
| **Endpoint · N=7**<br>每步更新完成后，约束 mask 外部；前 7 步启用 | ![endpoint_auto](assets/471dfaece9998fa700d1.jpg)<br>**编辑 2 / 保存 2** | ![endpoint_gt](assets/325744dd927fca229c40.jpg)<br>**编辑 1 / 保存 2** |
| **RK2 · N=7**<br>中点和终点均受控；前 7 步启用 | ![rk2_auto](assets/da5a6758d7c3ed767be9.jpg)<br>**编辑 2 / 保存 1** | ![rk2_gt](assets/4c559f7cae4723b489aa.jpg)<br>**编辑 1 / 保存 2** |
| **RK2 · N=15**<br>中点和终点均受控；全部 15 步启用 | ![rk2_n15_auto](assets/4ebcd4ebd02f83f1cd2e.jpg)<br>**编辑 2 / 保存 2** | ![rk2_n15_gt](assets/44859a70a1288c641e4c.jpg)<br>**编辑 1 / 保存 2** |

[返回头部案例索引](#head-index)


---

---

## 人形主体头部

<a id="synth_0000"></a>
## synth_0000：head → robot

**原始描述：** A alien at a city

**目标描述：** A alien with robot head at a city

**预期范围变化：** 基本不变

### 原图与控制区域

| 原始输入图片 | 自动 mask | GT mask |
| --- | --- | --- |
| ![Source](assets/cc5f01ed208f72709680.png) | ![Automatic mask](assets/synth_0000_auto_control_mask.png) | ![GT control mask](assets/synth_0000_gt_control_mask.png) |

白色＝允许编辑，黑色＝受保护区域。两张 mask 均为运行配置指定的实际输入，未平滑或额外扩张。

### 生成结果：固定左右列

| 控制方法与时长 | 使用自动 mask | 使用 GT mask |
| --- | --- | --- |
| **Endpoint · N=7**<br>每步更新完成后，约束 mask 外部；前 7 步启用 | ![endpoint_auto](assets/f75ab332592a27e58409.jpg)<br>**编辑 2 / 保存 0** | ![endpoint_gt](assets/a257c0a33f1eafb8268d.jpg)<br>**编辑 2 / 保存 1** |
| **RK2 · N=7**<br>中点和终点均受控；前 7 步启用 | ![rk2_auto](assets/74649f30ce1c031a7a47.jpg)<br>**编辑 2 / 保存 0** | ![rk2_gt](assets/9581d56bbfd0e558ca7c.jpg)<br>**编辑 1 / 保存 1** |
| **RK2 · N=15**<br>中点和终点均受控；全部 15 步启用 | ![rk2_n15_auto](assets/67bb0dce9fdd881da0dc.jpg)<br>**编辑 2 / 保存 0** | ![rk2_n15_gt](assets/66dd7a5b0f6904940f11.jpg)<br>**编辑 2 / 保存 2** |

[返回头部案例索引](#head-index)


---

<a id="synth_0001"></a>
## synth_0001：head → bear

**原始描述：** A robot at a school

**目标描述：** A robot with bear head at a school

**预期范围变化：** 基本不变

### 原图与控制区域

| 原始输入图片 | 自动 mask | GT mask |
| --- | --- | --- |
| ![Source](assets/b618aa27f8557521bf28.png) | ![Automatic mask](assets/synth_0001_auto_control_mask.png) | ![GT control mask](assets/synth_0001_gt_control_mask.png) |

白色＝允许编辑，黑色＝受保护区域。两张 mask 均为运行配置指定的实际输入，未平滑或额外扩张。

### 生成结果：固定左右列

| 控制方法与时长 | 使用自动 mask | 使用 GT mask |
| --- | --- | --- |
| **Endpoint · N=7**<br>每步更新完成后，约束 mask 外部；前 7 步启用 | ![endpoint_auto](assets/7a28b54fc621200e336b.jpg)<br>**编辑 2 / 保存 0** | ![endpoint_gt](assets/c80c7179ef80baf2bd43.jpg)<br>**编辑 2 / 保存 1** |
| **RK2 · N=7**<br>中点和终点均受控；前 7 步启用 | ![rk2_auto](assets/9b4e03dd61ad35904ef3.jpg)<br>**编辑 2 / 保存 1** | ![rk2_gt](assets/1035a0508029360581ce.jpg)<br>**编辑 2 / 保存 1** |
| **RK2 · N=15**<br>中点和终点均受控；全部 15 步启用 | ![rk2_n15_auto](assets/53668842a90f2679ab71.jpg)<br>**编辑 2 / 保存 1** | ![rk2_n15_gt](assets/ae67dadba3bfcf4d18fe.jpg)<br>**编辑 2 / 保存 2** |

[返回头部案例索引](#head-index)


---

<a id="synth_0002"></a>
## synth_0002：head → bear

**原始描述：** A robot at a park

**目标描述：** A robot with bear head at a park

**预期范围变化：** 基本不变

### 原图与控制区域

| 原始输入图片 | 自动 mask | GT mask |
| --- | --- | --- |
| ![Source](assets/06153f9c16dffc17bfd7.png) | ![Automatic mask](assets/synth_0002_auto_control_mask.png) | ![GT control mask](assets/synth_0002_gt_control_mask.png) |

白色＝允许编辑，黑色＝受保护区域。两张 mask 均为运行配置指定的实际输入，未平滑或额外扩张。

### 生成结果：固定左右列

| 控制方法与时长 | 使用自动 mask | 使用 GT mask |
| --- | --- | --- |
| **Endpoint · N=7**<br>每步更新完成后，约束 mask 外部；前 7 步启用 | ![endpoint_auto](assets/952019ca8fcf70fb336a.jpg)<br>**编辑 1 / 保存 0** | ![endpoint_gt](assets/183283f149133237bca2.jpg)<br>**编辑 1 / 保存 2** |
| **RK2 · N=7**<br>中点和终点均受控；前 7 步启用 | ![rk2_auto](assets/0a5914f11a58221f1897.jpg)<br>**编辑 0 / 保存 0** | ![rk2_gt](assets/ced3661635c438f7d04d.jpg)<br>**编辑 2 / 保存 2** |
| **RK2 · N=15**<br>中点和终点均受控；全部 15 步启用 | ![rk2_n15_auto](assets/1a6aca998353e35d628f.jpg)<br>**编辑 0 / 保存 0** | ![rk2_n15_gt](assets/d47ddc1805fc9d5de07d.jpg)<br>**编辑 2 / 保存 2** |

[返回头部案例索引](#head-index)


---

<a id="synth_0003"></a>
## synth_0003：head → robot

**原始描述：** A alien at a museum

**目标描述：** A alien with robot head at a museum

**预期范围变化：** 基本不变

### 原图与控制区域

| 原始输入图片 | 自动 mask | GT mask |
| --- | --- | --- |
| ![Source](assets/5a822543d05f3072ff24.png) | ![Automatic mask](assets/synth_0003_auto_control_mask.png) | ![GT control mask](assets/synth_0003_gt_control_mask.png) |

白色＝允许编辑，黑色＝受保护区域。两张 mask 均为运行配置指定的实际输入，未平滑或额外扩张。

### 生成结果：固定左右列

| 控制方法与时长 | 使用自动 mask | 使用 GT mask |
| --- | --- | --- |
| **Endpoint · N=7**<br>每步更新完成后，约束 mask 外部；前 7 步启用 | ![endpoint_auto](assets/99ac3d73b182b82575c6.jpg)<br>**编辑 2 / 保存 0** | ![endpoint_gt](assets/3cfa77eaf944eb7ac4c3.jpg)<br>**编辑 2 / 保存 2** |
| **RK2 · N=7**<br>中点和终点均受控；前 7 步启用 | ![rk2_auto](assets/999d0421ce344ff80c51.jpg)<br>**编辑 2 / 保存 0** | ![rk2_gt](assets/1dfdf9fdc6bc3fb37290.jpg)<br>**编辑 2 / 保存 2** |
| **RK2 · N=15**<br>中点和终点均受控；全部 15 步启用 | ![rk2_n15_auto](assets/ba335befcdb012b8052e.jpg)<br>**编辑 2 / 保存 1** | ![rk2_n15_gt](assets/cc6975b56baa71ade62a.jpg)<br>**编辑 2 / 保存 2** |

[返回头部案例索引](#head-index)


---

<a id="synth_0004"></a>
## synth_0004：head → tattooed

**原始描述：** A robot at a office

**目标描述：** A robot with tattooed head at a office

**预期范围变化：** 基本不变

### 原图与控制区域

| 原始输入图片 | 自动 mask | GT mask |
| --- | --- | --- |
| ![Source](assets/95d43a51e84af560d595.png) | ![Automatic mask](assets/synth_0004_auto_control_mask.png) | ![GT control mask](assets/synth_0004_gt_control_mask.png) |

白色＝允许编辑，黑色＝受保护区域。两张 mask 均为运行配置指定的实际输入，未平滑或额外扩张。

### 生成结果：固定左右列

| 控制方法与时长 | 使用自动 mask | 使用 GT mask |
| --- | --- | --- |
| **Endpoint · N=7**<br>每步更新完成后，约束 mask 外部；前 7 步启用 | ![endpoint_auto](assets/752f1430984b9bff42d1.jpg)<br>**编辑 0 / 保存 0** | ![endpoint_gt](assets/99e28ba627698acf648d.jpg)<br>**编辑 0 / 保存 1** |
| **RK2 · N=7**<br>中点和终点均受控；前 7 步启用 | ![rk2_auto](assets/4bd02813acd1822079dd.jpg)<br>**编辑 0 / 保存 1** | ![rk2_gt](assets/1b2332528e2c0fe1864b.jpg)<br>**编辑 0 / 保存 1** |
| **RK2 · N=15**<br>中点和终点均受控；全部 15 步启用 | ![rk2_n15_auto](assets/14cb14a4f0b4b0b424f2.jpg)<br>**编辑 1 / 保存 2** | ![rk2_n15_gt](assets/4991c8cd9fdd6f528bce.jpg)<br>**编辑 1 / 保存 2** |

[返回头部案例索引](#head-index)


---

<a id="synth_0005"></a>
## synth_0005：head → robot

**原始描述：** A man at a gym

**目标描述：** A man with robot head at a gym

**预期范围变化：** 基本不变

### 原图与控制区域

| 原始输入图片 | 自动 mask | GT mask |
| --- | --- | --- |
| ![Source](assets/a0e6abb84c900968be16.png) | ![Automatic mask](assets/synth_0005_auto_control_mask.png) | ![GT control mask](assets/synth_0005_gt_control_mask.png) |

白色＝允许编辑，黑色＝受保护区域。两张 mask 均为运行配置指定的实际输入，未平滑或额外扩张。

### 生成结果：固定左右列

| 控制方法与时长 | 使用自动 mask | 使用 GT mask |
| --- | --- | --- |
| **Endpoint · N=7**<br>每步更新完成后，约束 mask 外部；前 7 步启用 | ![endpoint_auto](assets/4a7daad6bedd9370bda3.jpg)<br>**编辑 2 / 保存 1** | ![endpoint_gt](assets/cf6cffb16b6f4d7d4b76.jpg)<br>**编辑 2 / 保存 1** |
| **RK2 · N=7**<br>中点和终点均受控；前 7 步启用 | ![rk2_auto](assets/9773da4b12be4f7501b5.jpg)<br>**编辑 2 / 保存 1** | ![rk2_gt](assets/b7c9e48a575b635ae3b3.jpg)<br>**编辑 0 / 保存 1** |
| **RK2 · N=15**<br>中点和终点均受控；全部 15 步启用 | ![rk2_n15_auto](assets/090e1dd3ff3e90a9e01e.jpg)<br>**编辑 1 / 保存 2** | ![rk2_n15_gt](assets/725623bb1bba8b0324ae.jpg)<br>**编辑 2 / 保存 2** |

[返回头部案例索引](#head-index)


---

<a id="synth_0006"></a>
## synth_0006：head → robot

**原始描述：** A girl at a beach

**目标描述：** A girl with robot head at a beach

**预期范围变化：** 基本不变

### 原图与控制区域

| 原始输入图片 | 自动 mask | GT mask |
| --- | --- | --- |
| ![Source](assets/625cb403a9a4bd5a187d.png) | ![Automatic mask](assets/synth_0006_auto_control_mask.png) | ![GT control mask](assets/synth_0006_gt_control_mask.png) |

白色＝允许编辑，黑色＝受保护区域。两张 mask 均为运行配置指定的实际输入，未平滑或额外扩张。

### 生成结果：固定左右列

| 控制方法与时长 | 使用自动 mask | 使用 GT mask |
| --- | --- | --- |
| **Endpoint · N=7**<br>每步更新完成后，约束 mask 外部；前 7 步启用 | ![endpoint_auto](assets/b6540f99f5ee075189fe.jpg)<br>**编辑 0 / 保存 1** | ![endpoint_gt](assets/0bcfefc0138f2334e849.jpg)<br>**编辑 0 / 保存 2** |
| **RK2 · N=7**<br>中点和终点均受控；前 7 步启用 | ![rk2_auto](assets/3b5583243790aea9672d.jpg)<br>**编辑 0 / 保存 1** | ![rk2_gt](assets/3320280fa57b6f227c82.jpg)<br>**编辑 0 / 保存 0** |
| **RK2 · N=15**<br>中点和终点均受控；全部 15 步启用 | ![rk2_n15_auto](assets/a7503c02983087248e38.jpg)<br>**编辑 0 / 保存 1** | ![rk2_n15_gt](assets/343ab356bc8f6f05987b.jpg)<br>**编辑 0 / 保存 2** |

[返回头部案例索引](#head-index)


---

<a id="synth_0007"></a>
## synth_0007：head → robot

**原始描述：** A alien at a school

**目标描述：** A alien with robot head at a school

**预期范围变化：** 基本不变

### 原图与控制区域

| 原始输入图片 | 自动 mask | GT mask |
| --- | --- | --- |
| ![Source](assets/e68c9359b05c1bb262f9.png) | ![Automatic mask](assets/synth_0007_auto_control_mask.png) | ![GT control mask](assets/synth_0007_gt_control_mask.png) |

白色＝允许编辑，黑色＝受保护区域。两张 mask 均为运行配置指定的实际输入，未平滑或额外扩张。

### 生成结果：固定左右列

| 控制方法与时长 | 使用自动 mask | 使用 GT mask |
| --- | --- | --- |
| **Endpoint · N=7**<br>每步更新完成后，约束 mask 外部；前 7 步启用 | ![endpoint_auto](assets/8b5a06981164a8931965.jpg)<br>**编辑 1 / 保存 1** | ![endpoint_gt](assets/808d119895288705d383.jpg)<br>**编辑 2 / 保存 1** |
| **RK2 · N=7**<br>中点和终点均受控；前 7 步启用 | ![rk2_auto](assets/8b193a11c8ada8bbb9b2.jpg)<br>**编辑 1 / 保存 1** | ![rk2_gt](assets/53ceec04f120ce567f27.jpg)<br>**编辑 2 / 保存 1** |
| **RK2 · N=15**<br>中点和终点均受控；全部 15 步启用 | ![rk2_n15_auto](assets/32f9366e6eecf041ef60.jpg)<br>**编辑 0 / 保存 1** | ![rk2_n15_gt](assets/347eb8236301f57f7e46.jpg)<br>**编辑 2 / 保存 2** |

[返回头部案例索引](#head-index)


---

<a id="synth_0008"></a>
## synth_0008：head → alien

**原始描述：** A robot at a park

**目标描述：** A robot with alien head at a park

**预期范围变化：** 基本不变

### 原图与控制区域

| 原始输入图片 | 自动 mask | GT mask |
| --- | --- | --- |
| ![Source](assets/a9e11e1f221eb73b9cca.png) | ![Automatic mask](assets/synth_0008_auto_control_mask.png) | ![GT control mask](assets/synth_0008_gt_control_mask.png) |

白色＝允许编辑，黑色＝受保护区域。两张 mask 均为运行配置指定的实际输入，未平滑或额外扩张。

### 生成结果：固定左右列

| 控制方法与时长 | 使用自动 mask | 使用 GT mask |
| --- | --- | --- |
| **Endpoint · N=7**<br>每步更新完成后，约束 mask 外部；前 7 步启用 | ![endpoint_auto](assets/ac99bb329aae4de3575c.jpg)<br>**编辑 2 / 保存 1** | ![endpoint_gt](assets/55c7c9b8c311bdbcb339.jpg)<br>**编辑 2 / 保存 2** |
| **RK2 · N=7**<br>中点和终点均受控；前 7 步启用 | ![rk2_auto](assets/4918508292a9b271e105.jpg)<br>**编辑 2 / 保存 1** | ![rk2_gt](assets/0494021cb56bfa3d993e.jpg)<br>**编辑 2 / 保存 1** |
| **RK2 · N=15**<br>中点和终点均受控；全部 15 步启用 | ![rk2_n15_auto](assets/68baca8a3445c731a659.jpg)<br>**编辑 2 / 保存 2** | ![rk2_n15_gt](assets/60193f9d7b54ee9bf5e2.jpg)<br>**编辑 2 / 保存 2** |

[返回头部案例索引](#head-index)


---

<a id="synth_0009"></a>
## synth_0009：head → bear

**原始描述：** A alien at a museum

**目标描述：** A alien with bear head at a museum

**预期范围变化：** 基本不变

### 原图与控制区域

| 原始输入图片 | 自动 mask | GT mask |
| --- | --- | --- |
| ![Source](assets/c7098c982dbc8f357439.png) | ![Automatic mask](assets/synth_0009_auto_control_mask.png) | ![GT control mask](assets/synth_0009_gt_control_mask.png) |

白色＝允许编辑，黑色＝受保护区域。两张 mask 均为运行配置指定的实际输入，未平滑或额外扩张。

### 生成结果：固定左右列

| 控制方法与时长 | 使用自动 mask | 使用 GT mask |
| --- | --- | --- |
| **Endpoint · N=7**<br>每步更新完成后，约束 mask 外部；前 7 步启用 | ![endpoint_auto](assets/8b77b1791bb16922f747.jpg)<br>**编辑 0 / 保存 1** | ![endpoint_gt](assets/f371a25cd6f885274a9f.jpg)<br>**编辑 0 / 保存 1** |
| **RK2 · N=7**<br>中点和终点均受控；前 7 步启用 | ![rk2_auto](assets/c0124be4f5c8ec1eee1e.jpg)<br>**编辑 0 / 保存 1** | ![rk2_gt](assets/7f434a72a6a842138c25.jpg)<br>**编辑 0 / 保存 1** |
| **RK2 · N=15**<br>中点和终点均受控；全部 15 步启用 | ![rk2_n15_auto](assets/507abcb1080e7f50dd3e.jpg)<br>**编辑 0 / 保存 2** | ![rk2_n15_gt](assets/011c107c10c2e426df98.jpg)<br>**编辑 0 / 保存 2** |

[返回头部案例索引](#head-index)


---
