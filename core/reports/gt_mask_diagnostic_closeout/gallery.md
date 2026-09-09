# GT mask 诊断：59 个例子的完整对比

**所有例子使用同一布局：左列为自动 mask，右列为 GT mask；三行依次为 Endpoint N=7、RK2 N=7、RK2 N=15。**

- 横向看：同一种控制方法，更换 mask 后的区别。
- 纵向看：同一种 mask，更换控制方法或控制时长后的区别。
- N 是从第 0 步开始连续控制的步数，总生成步数为 15；N=7 后还有 8 步自由更新。
- 自动 mask 不是“不控制”，也不是原始 FYS 结果。GT mask 是原部位标注转换得到的控制区域，不一定覆盖目标扩张所需的范围。
- 分数为单一评分者的 0–2 分：**编辑**是局部修改成功程度，**保存**是非目标区域保持程度。高保存分不代表编辑成功。
- 图片未经修饰。该图集已显示方法身份，不用于独立盲评。

## 案例索引

- [synth_0000：head → robot](#synth_0000)
- [synth_0001：head → bear](#synth_0001)
- [synth_0002：head → bear](#synth_0002)
- [synth_0003：head → robot](#synth_0003)
- [synth_0004：head → tattooed](#synth_0004)
- [synth_0005：head → robot](#synth_0005)
- [synth_0006：head → robot](#synth_0006)
- [synth_0007：head → robot](#synth_0007)
- [synth_0008：head → alien](#synth_0008)
- [synth_0009：head → bear](#synth_0009)
- [synth_0010：torso → batman](#synth_0010)
- [synth_0011：torso → spiderman](#synth_0011)
- [synth_0012：torso → spiderman](#synth_0012)
- [synth_0013：torso → uniform](#synth_0013)
- [synth_0015：torso → formal-suit](#synth_0015)
- [synth_0016：torso → armor](#synth_0016)
- [synth_0017：torso → robotic-parts](#synth_0017)
- [synth_0018：torso → armor](#synth_0018)
- [synth_0019：hair → Wavy](#synth_0019)
- [synth_0020：hair → Curls](#synth_0020)
- [synth_0021：hair → Afro](#synth_0021)
- [synth_0022：hair → Kinky](#synth_0022)
- [synth_0023：hair → blond](#synth_0023)
- [synth_0024：hair → Curley](#synth_0024)
- [synth_0025：hair → Botticelli-Curls](#synth_0025)
- [synth_0026：hair → Curls](#synth_0026)
- [synth_0027：hair → Curls](#synth_0027)
- [synth_0028：head → dragon](#synth_0028)
- [synth_0029：head → lion](#synth_0029)
- [synth_0030：head → dog](#synth_0030)
- [synth_0031：head → dragon](#synth_0031)
- [synth_0032：head → dragon](#synth_0032)
- [synth_0033：head → cat](#synth_0033)
- [synth_0034：head → unicorn](#synth_0034)
- [synth_0035：head → cheetah](#synth_0035)
- [synth_0036：head → lion](#synth_0036)
- [synth_0037：head → dragon](#synth_0037)
- [synth_0038：head → dragon](#synth_0038)
- [synth_0039：head → unicorn](#synth_0039)
- [synth_0040：head → tiger](#synth_0040)
- [synth_0041：head → panda](#synth_0041)
- [synth_0042：head → cheetah](#synth_0042)
- [synth_0043：head → dragon](#synth_0043)
- [synth_0044：head → lion](#synth_0044)
- [synth_0045：head → panda](#synth_0045)
- [synth_0046：car body → armored](#synth_0046)
- [synth_0047：car body → futuristic](#synth_0047)
- [synth_0048：car body → rusted](#synth_0048)
- [synth_0049：car body → neon-lit](#synth_0049)
- [synth_0050：car hood → black](#synth_0050)
- [synth_0051：car hood → vinyl-art](#synth_0051)
- [synth_0052：car hood → Digital-Camouflage](#synth_0052)
- [synth_0053：car hood → Destroyed](#synth_0053)
- [synth_0054：car hood → Rusty](#synth_0054)
- [synth_0055：car hood → Graffiti](#synth_0055)
- [synth_0056：seat → fabric](#synth_0056)
- [synth_0057：seat → plastic](#synth_0057)
- [synth_0058：seat → rusted](#synth_0058)
- [synth_0059：seat → wooden](#synth_0059)

---

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

[返回案例索引](#案例索引)


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

[返回案例索引](#案例索引)


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

[返回案例索引](#案例索引)


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

[返回案例索引](#案例索引)


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

[返回案例索引](#案例索引)


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

[返回案例索引](#案例索引)


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

[返回案例索引](#案例索引)


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

[返回案例索引](#案例索引)


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

[返回案例索引](#案例索引)


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

[返回案例索引](#案例索引)


---

<a id="synth_0010"></a>
## synth_0010：torso → batman

**原始描述：** A robot at a school

**目标描述：** A robot with batman torso at a school

**预期范围变化：** 基本不变

### 原图与控制区域

| 原始输入图片 | 自动 mask | GT mask |
| --- | --- | --- |
| ![Source](assets/0f3cd46376625b70fd81.png) | ![Automatic mask](assets/synth_0010_auto_control_mask.png) | ![GT control mask](assets/synth_0010_gt_control_mask.png) |

白色＝允许编辑，黑色＝受保护区域。两张 mask 均为运行配置指定的实际输入，未平滑或额外扩张。

### 生成结果：固定左右列

| 控制方法与时长 | 使用自动 mask | 使用 GT mask |
| --- | --- | --- |
| **Endpoint · N=7**<br>每步更新完成后，约束 mask 外部；前 7 步启用 | ![endpoint_auto](assets/b8e0004cbb22e3d60c3f.jpg)<br>**编辑 2 / 保存 0** | ![endpoint_gt](assets/0349c559fa63b5bf4030.jpg)<br>**编辑 2 / 保存 1** |
| **RK2 · N=7**<br>中点和终点均受控；前 7 步启用 | ![rk2_auto](assets/e4b601ab0d44ce5ee73a.jpg)<br>**编辑 2 / 保存 0** | ![rk2_gt](assets/6edcf1366c243c5e33ea.jpg)<br>**编辑 2 / 保存 2** |
| **RK2 · N=15**<br>中点和终点均受控；全部 15 步启用 | ![rk2_n15_auto](assets/e843b65609e9a6d7802a.jpg)<br>**编辑 2 / 保存 0** | ![rk2_n15_gt](assets/d4a5a25917dbb0ff9c6a.jpg)<br>**编辑 2 / 保存 2** |

[返回案例索引](#案例索引)


---

<a id="synth_0011"></a>
## synth_0011：torso → spiderman

**原始描述：** A robot at a museum

**目标描述：** A robot with spiderman torso at a museum

**预期范围变化：** 基本不变

### 原图与控制区域

| 原始输入图片 | 自动 mask | GT mask |
| --- | --- | --- |
| ![Source](assets/d10334437e175ada776b.png) | ![Automatic mask](assets/synth_0011_auto_control_mask.png) | ![GT control mask](assets/synth_0011_gt_control_mask.png) |

白色＝允许编辑，黑色＝受保护区域。两张 mask 均为运行配置指定的实际输入，未平滑或额外扩张。

### 生成结果：固定左右列

| 控制方法与时长 | 使用自动 mask | 使用 GT mask |
| --- | --- | --- |
| **Endpoint · N=7**<br>每步更新完成后，约束 mask 外部；前 7 步启用 | ![endpoint_auto](assets/fa9c496e503d8f85f544.jpg)<br>**编辑 2 / 保存 1** | ![endpoint_gt](assets/22a63ae216a20f58f7fa.jpg)<br>**编辑 2 / 保存 1** |
| **RK2 · N=7**<br>中点和终点均受控；前 7 步启用 | ![rk2_auto](assets/b972e6fe3cb48126b061.jpg)<br>**编辑 2 / 保存 1** | ![rk2_gt](assets/4127b0a1ce4b0c5ce2a2.jpg)<br>**编辑 2 / 保存 1** |
| **RK2 · N=15**<br>中点和终点均受控；全部 15 步启用 | ![rk2_n15_auto](assets/481220ae93f8202a280a.jpg)<br>**编辑 2 / 保存 2** | ![rk2_n15_gt](assets/e243c7f2636ded8286bc.jpg)<br>**编辑 2 / 保存 2** |

[返回案例索引](#案例索引)


---

<a id="synth_0012"></a>
## synth_0012：torso → spiderman

**原始描述：** A robot at a museum

**目标描述：** A robot with spiderman torso at a museum

**预期范围变化：** 基本不变

### 原图与控制区域

| 原始输入图片 | 自动 mask | GT mask |
| --- | --- | --- |
| ![Source](assets/3b0bd5d4f2562425f902.png) | ![Automatic mask](assets/synth_0012_auto_control_mask.png) | ![GT control mask](assets/synth_0012_gt_control_mask.png) |

白色＝允许编辑，黑色＝受保护区域。两张 mask 均为运行配置指定的实际输入，未平滑或额外扩张。

### 生成结果：固定左右列

| 控制方法与时长 | 使用自动 mask | 使用 GT mask |
| --- | --- | --- |
| **Endpoint · N=7**<br>每步更新完成后，约束 mask 外部；前 7 步启用 | ![endpoint_auto](assets/7c8183e2982a181f0bd7.jpg)<br>**编辑 2 / 保存 0** | ![endpoint_gt](assets/f5fef0766bb3e900d9db.jpg)<br>**编辑 2 / 保存 1** |
| **RK2 · N=7**<br>中点和终点均受控；前 7 步启用 | ![rk2_auto](assets/c456915ce30a091c997c.jpg)<br>**编辑 1 / 保存 0** | ![rk2_gt](assets/9bf3a591d92148ce7a7a.jpg)<br>**编辑 2 / 保存 1** |
| **RK2 · N=15**<br>中点和终点均受控；全部 15 步启用 | ![rk2_n15_auto](assets/d5f76ea90228a98fe037.jpg)<br>**编辑 2 / 保存 0** | ![rk2_n15_gt](assets/81a3b78589dfb463aafe.jpg)<br>**编辑 2 / 保存 1** |

[返回案例索引](#案例索引)


---

<a id="synth_0013"></a>
## synth_0013：torso → uniform

**原始描述：** A alien at a school

**目标描述：** A alien with uniform torso at a school

**预期范围变化：** 基本不变

### 原图与控制区域

| 原始输入图片 | 自动 mask | GT mask |
| --- | --- | --- |
| ![Source](assets/f4b464d3b648c4220b6d.png) | ![Automatic mask](assets/synth_0013_auto_control_mask.png) | ![GT control mask](assets/synth_0013_gt_control_mask.png) |

白色＝允许编辑，黑色＝受保护区域。两张 mask 均为运行配置指定的实际输入，未平滑或额外扩张。

### 生成结果：固定左右列

| 控制方法与时长 | 使用自动 mask | 使用 GT mask |
| --- | --- | --- |
| **Endpoint · N=7**<br>每步更新完成后，约束 mask 外部；前 7 步启用 | ![endpoint_auto](assets/6958fa290bc30c820030.jpg)<br>**编辑 2 / 保存 1** | ![endpoint_gt](assets/786dcf766ca052bde50d.jpg)<br>**编辑 2 / 保存 1** |
| **RK2 · N=7**<br>中点和终点均受控；前 7 步启用 | ![rk2_auto](assets/92b3e5177619a87c4f50.jpg)<br>**编辑 2 / 保存 1** | ![rk2_gt](assets/4c84599fb5aa9cb4c4f7.jpg)<br>**编辑 2 / 保存 2** |
| **RK2 · N=15**<br>中点和终点均受控；全部 15 步启用 | ![rk2_n15_auto](assets/f816c13f9f0dd00b842f.jpg)<br>**编辑 2 / 保存 1** | ![rk2_n15_gt](assets/2d507376d7714fe3bce2.jpg)<br>**编辑 2 / 保存 2** |

[返回案例索引](#案例索引)


---

<a id="synth_0015"></a>
## synth_0015：torso → formal-suit

**原始描述：** A robot at a restaurant

**目标描述：** A robot with formal-suit torso at a restaurant

**预期范围变化：** 基本不变

### 原图与控制区域

| 原始输入图片 | 自动 mask | GT mask |
| --- | --- | --- |
| ![Source](assets/d9b261fd0c97b210553c.png) | ![Automatic mask](assets/synth_0015_auto_control_mask.png) | ![GT control mask](assets/synth_0015_gt_control_mask.png) |

白色＝允许编辑，黑色＝受保护区域。两张 mask 均为运行配置指定的实际输入，未平滑或额外扩张。

### 生成结果：固定左右列

| 控制方法与时长 | 使用自动 mask | 使用 GT mask |
| --- | --- | --- |
| **Endpoint · N=7**<br>每步更新完成后，约束 mask 外部；前 7 步启用 | ![endpoint_auto](assets/f477f0d6039e59ea6b54.jpg)<br>**编辑 1 / 保存 0** | ![endpoint_gt](assets/e8459f6a71476a8518b1.jpg)<br>**编辑 2 / 保存 2** |
| **RK2 · N=7**<br>中点和终点均受控；前 7 步启用 | ![rk2_auto](assets/2688579a67e90ade55be.jpg)<br>**编辑 2 / 保存 1** | ![rk2_gt](assets/2de2ac43883048c73330.jpg)<br>**编辑 2 / 保存 2** |
| **RK2 · N=15**<br>中点和终点均受控；全部 15 步启用 | ![rk2_n15_auto](assets/6942c41d9534a788d897.jpg)<br>**编辑 1 / 保存 0** | ![rk2_n15_gt](assets/530006ce0716620f3320.jpg)<br>**编辑 2 / 保存 2** |

[返回案例索引](#案例索引)


---

<a id="synth_0016"></a>
## synth_0016：torso → armor

**原始描述：** A girl at a stadium

**目标描述：** A girl with armor torso at a stadium

**预期范围变化：** 基本不变

### 原图与控制区域

| 原始输入图片 | 自动 mask | GT mask |
| --- | --- | --- |
| ![Source](assets/b1322f0354f51bb6edf5.png) | ![Automatic mask](assets/synth_0016_auto_control_mask.png) | ![GT control mask](assets/synth_0016_gt_control_mask.png) |

白色＝允许编辑，黑色＝受保护区域。两张 mask 均为运行配置指定的实际输入，未平滑或额外扩张。

### 生成结果：固定左右列

| 控制方法与时长 | 使用自动 mask | 使用 GT mask |
| --- | --- | --- |
| **Endpoint · N=7**<br>每步更新完成后，约束 mask 外部；前 7 步启用 | ![endpoint_auto](assets/9630f10533f642a72279.jpg)<br>**编辑 2 / 保存 1** | ![endpoint_gt](assets/7d3167100f7e64ae6078.jpg)<br>**编辑 2 / 保存 2** |
| **RK2 · N=7**<br>中点和终点均受控；前 7 步启用 | ![rk2_auto](assets/8d000ce08b20f700d551.jpg)<br>**编辑 2 / 保存 1** | ![rk2_gt](assets/4df8e041a47a2aa1f3c2.jpg)<br>**编辑 2 / 保存 2** |
| **RK2 · N=15**<br>中点和终点均受控；全部 15 步启用 | ![rk2_n15_auto](assets/6603c0ee44413d7aed1f.jpg)<br>**编辑 2 / 保存 2** | ![rk2_n15_gt](assets/452a6917213c9c056ceb.jpg)<br>**编辑 2 / 保存 2** |

[返回案例索引](#案例索引)


---

<a id="synth_0017"></a>
## synth_0017：torso → robotic-parts

**原始描述：** A dinosaur at a museum

**目标描述：** A dinosaur with robotic-parts torso at a museum

**预期范围变化：** 基本不变

### 原图与控制区域

| 原始输入图片 | 自动 mask | GT mask |
| --- | --- | --- |
| ![Source](assets/245f1623447aded5cf75.png) | ![Automatic mask](assets/synth_0017_auto_control_mask.png) | ![GT control mask](assets/synth_0017_gt_control_mask.png) |

白色＝允许编辑，黑色＝受保护区域。两张 mask 均为运行配置指定的实际输入，未平滑或额外扩张。

### 生成结果：固定左右列

| 控制方法与时长 | 使用自动 mask | 使用 GT mask |
| --- | --- | --- |
| **Endpoint · N=7**<br>每步更新完成后，约束 mask 外部；前 7 步启用 | ![endpoint_auto](assets/682051b2537e29ccabfb.jpg)<br>**编辑 1 / 保存 1** | ![endpoint_gt](assets/f789f9920faf24595ee1.jpg)<br>**编辑 2 / 保存 0** |
| **RK2 · N=7**<br>中点和终点均受控；前 7 步启用 | ![rk2_auto](assets/6298840dacbabc5c0f1b.jpg)<br>**编辑 1 / 保存 0** | ![rk2_gt](assets/3b0b040e7c2fe7cacac6.jpg)<br>**编辑 2 / 保存 1** |
| **RK2 · N=15**<br>中点和终点均受控；全部 15 步启用 | ![rk2_n15_auto](assets/635d36844854e8663b45.jpg)<br>**编辑 2 / 保存 2** | ![rk2_n15_gt](assets/744d150b72b870de4559.jpg)<br>**编辑 2 / 保存 2** |

[返回案例索引](#案例索引)


---

<a id="synth_0018"></a>
## synth_0018：torso → armor

**原始描述：** A boy at a restaurant

**目标描述：** A boy with armor torso at a restaurant

**预期范围变化：** 基本不变

### 原图与控制区域

| 原始输入图片 | 自动 mask | GT mask |
| --- | --- | --- |
| ![Source](assets/00107db62f4772225a0b.png) | ![Automatic mask](assets/synth_0018_auto_control_mask.png) | ![GT control mask](assets/synth_0018_gt_control_mask.png) |

白色＝允许编辑，黑色＝受保护区域。两张 mask 均为运行配置指定的实际输入，未平滑或额外扩张。

### 生成结果：固定左右列

| 控制方法与时长 | 使用自动 mask | 使用 GT mask |
| --- | --- | --- |
| **Endpoint · N=7**<br>每步更新完成后，约束 mask 外部；前 7 步启用 | ![endpoint_auto](assets/2718b29a20585dda5a4d.jpg)<br>**编辑 2 / 保存 1** | ![endpoint_gt](assets/ba7d7caab05093535b34.jpg)<br>**编辑 2 / 保存 1** |
| **RK2 · N=7**<br>中点和终点均受控；前 7 步启用 | ![rk2_auto](assets/35439c2eedbb6934b62b.jpg)<br>**编辑 2 / 保存 1** | ![rk2_gt](assets/42d254ecc1e4dd378715.jpg)<br>**编辑 2 / 保存 1** |
| **RK2 · N=15**<br>中点和终点均受控；全部 15 步启用 | ![rk2_n15_auto](assets/0216d6a2c249c8f47a82.jpg)<br>**编辑 2 / 保存 1** | ![rk2_n15_gt](assets/7fc72a73561bf721af91.jpg)<br>**编辑 2 / 保存 2** |

[返回案例索引](#案例索引)


---

<a id="synth_0019"></a>
## synth_0019：hair → Wavy

**原始描述：** A Portrait of girl at a forest

**目标描述：** A Portrait of girl with Wavy hair at a forest

**预期范围变化：** 基本不变

### 原图与控制区域

| 原始输入图片 | 自动 mask | GT mask |
| --- | --- | --- |
| ![Source](assets/a885da67a93ec72e2926.png) | ![Automatic mask](assets/synth_0019_auto_control_mask.png) | ![GT control mask](assets/synth_0019_gt_control_mask.png) |

白色＝允许编辑，黑色＝受保护区域。两张 mask 均为运行配置指定的实际输入，未平滑或额外扩张。

### 生成结果：固定左右列

| 控制方法与时长 | 使用自动 mask | 使用 GT mask |
| --- | --- | --- |
| **Endpoint · N=7**<br>每步更新完成后，约束 mask 外部；前 7 步启用 | ![endpoint_auto](assets/3f75a180e8ed0e963e2e.jpg)<br>**编辑 2 / 保存 1** | ![endpoint_gt](assets/51f36622f6d1a0d629d0.jpg)<br>**编辑 2 / 保存 2** |
| **RK2 · N=7**<br>中点和终点均受控；前 7 步启用 | ![rk2_auto](assets/044b1dc9a1ced3806be0.jpg)<br>**编辑 2 / 保存 1** | ![rk2_gt](assets/67ad26cda7a8e3cb6f55.jpg)<br>**编辑 2 / 保存 2** |
| **RK2 · N=15**<br>中点和终点均受控；全部 15 步启用 | ![rk2_n15_auto](assets/40851c64b00c12f25515.jpg)<br>**编辑 2 / 保存 2** | ![rk2_n15_gt](assets/5c134e0229f2fa45ce1c.jpg)<br>**编辑 2 / 保存 2** |

[返回案例索引](#案例索引)


---

<a id="synth_0020"></a>
## synth_0020：hair → Curls

**原始描述：** A Portrait of boy at a park

**目标描述：** A Portrait of boy with Curls hair at a park

**预期范围变化：** 基本不变

### 原图与控制区域

| 原始输入图片 | 自动 mask | GT mask |
| --- | --- | --- |
| ![Source](assets/c74e49963c073745b1e2.png) | ![Automatic mask](assets/synth_0020_auto_control_mask.png) | ![GT control mask](assets/synth_0020_gt_control_mask.png) |

白色＝允许编辑，黑色＝受保护区域。两张 mask 均为运行配置指定的实际输入，未平滑或额外扩张。

### 生成结果：固定左右列

| 控制方法与时长 | 使用自动 mask | 使用 GT mask |
| --- | --- | --- |
| **Endpoint · N=7**<br>每步更新完成后，约束 mask 外部；前 7 步启用 | ![endpoint_auto](assets/e57c6a2eaae10df1bcca.jpg)<br>**编辑 2 / 保存 2** | ![endpoint_gt](assets/73b382e7e256fb486a34.jpg)<br>**编辑 2 / 保存 2** |
| **RK2 · N=7**<br>中点和终点均受控；前 7 步启用 | ![rk2_auto](assets/d766b88a1726578336f8.jpg)<br>**编辑 2 / 保存 2** | ![rk2_gt](assets/ca7e6d291fc123ecfcdf.jpg)<br>**编辑 2 / 保存 2** |
| **RK2 · N=15**<br>中点和终点均受控；全部 15 步启用 | ![rk2_n15_auto](assets/b7aa654b67304f1ae6f6.jpg)<br>**编辑 2 / 保存 2** | ![rk2_n15_gt](assets/c97b7d21363289704060.jpg)<br>**编辑 2 / 保存 2** |

[返回案例索引](#案例索引)


---

<a id="synth_0021"></a>
## synth_0021：hair → Afro

**原始描述：** A Portrait of boy at a beach

**目标描述：** A Portrait of boy with Afro hair at a beach

**预期范围变化：** 基本不变

### 原图与控制区域

| 原始输入图片 | 自动 mask | GT mask |
| --- | --- | --- |
| ![Source](assets/b536d178f0c163600f77.png) | ![Automatic mask](assets/synth_0021_auto_control_mask.png) | ![GT control mask](assets/synth_0021_gt_control_mask.png) |

白色＝允许编辑，黑色＝受保护区域。两张 mask 均为运行配置指定的实际输入，未平滑或额外扩张。

### 生成结果：固定左右列

| 控制方法与时长 | 使用自动 mask | 使用 GT mask |
| --- | --- | --- |
| **Endpoint · N=7**<br>每步更新完成后，约束 mask 外部；前 7 步启用 | ![endpoint_auto](assets/78c086324aa1fe7b0a4a.jpg)<br>**编辑 2 / 保存 2** | ![endpoint_gt](assets/a0bf63222fb1c3c33b99.jpg)<br>**编辑 2 / 保存 1** |
| **RK2 · N=7**<br>中点和终点均受控；前 7 步启用 | ![rk2_auto](assets/75c204a730b4df8b248d.jpg)<br>**编辑 2 / 保存 1** | ![rk2_gt](assets/b425c1ad9ce0c89f3964.jpg)<br>**编辑 2 / 保存 1** |
| **RK2 · N=15**<br>中点和终点均受控；全部 15 步启用 | ![rk2_n15_auto](assets/bbf51c83422dde7574fc.jpg)<br>**编辑 2 / 保存 2** | ![rk2_n15_gt](assets/faecc23d52a2549a59b1.jpg)<br>**编辑 2 / 保存 2** |

[返回案例索引](#案例索引)


---

<a id="synth_0022"></a>
## synth_0022：hair → Kinky

**原始描述：** A Portrait of boy at a park

**目标描述：** A Portrait of boy with Kinky hair at a park

**预期范围变化：** 基本不变

### 原图与控制区域

| 原始输入图片 | 自动 mask | GT mask |
| --- | --- | --- |
| ![Source](assets/532bf193aee67e561844.png) | ![Automatic mask](assets/synth_0022_auto_control_mask.png) | ![GT control mask](assets/synth_0022_gt_control_mask.png) |

白色＝允许编辑，黑色＝受保护区域。两张 mask 均为运行配置指定的实际输入，未平滑或额外扩张。

### 生成结果：固定左右列

| 控制方法与时长 | 使用自动 mask | 使用 GT mask |
| --- | --- | --- |
| **Endpoint · N=7**<br>每步更新完成后，约束 mask 外部；前 7 步启用 | ![endpoint_auto](assets/3f975d89c6476c191443.jpg)<br>**编辑 2 / 保存 2** | ![endpoint_gt](assets/fe4be7517310fbb9c30a.jpg)<br>**编辑 2 / 保存 2** |
| **RK2 · N=7**<br>中点和终点均受控；前 7 步启用 | ![rk2_auto](assets/7175f4f668c7ab1f9a4c.jpg)<br>**编辑 2 / 保存 2** | ![rk2_gt](assets/2518d7a0c63c6998b667.jpg)<br>**编辑 2 / 保存 2** |
| **RK2 · N=15**<br>中点和终点均受控；全部 15 步启用 | ![rk2_n15_auto](assets/c515aadff6661953503c.jpg)<br>**编辑 2 / 保存 2** | ![rk2_n15_gt](assets/944fd28759c75c2cd090.jpg)<br>**编辑 2 / 保存 2** |

[返回案例索引](#案例索引)


---

<a id="synth_0023"></a>
## synth_0023：hair → blond

**原始描述：** A Portrait of man at a beach

**目标描述：** A Portrait of man with blond hair at a beach

**预期范围变化：** 基本不变

### 原图与控制区域

| 原始输入图片 | 自动 mask | GT mask |
| --- | --- | --- |
| ![Source](assets/2eefa229af3c0f553c72.png) | ![Automatic mask](assets/synth_0023_auto_control_mask.png) | ![GT control mask](assets/synth_0023_gt_control_mask.png) |

白色＝允许编辑，黑色＝受保护区域。两张 mask 均为运行配置指定的实际输入，未平滑或额外扩张。

### 生成结果：固定左右列

| 控制方法与时长 | 使用自动 mask | 使用 GT mask |
| --- | --- | --- |
| **Endpoint · N=7**<br>每步更新完成后，约束 mask 外部；前 7 步启用 | ![endpoint_auto](assets/d9dd3b675f4bfbf8efd7.jpg)<br>**编辑 2 / 保存 2** | ![endpoint_gt](assets/a41e21511027d9dd5485.jpg)<br>**编辑 2 / 保存 1** |
| **RK2 · N=7**<br>中点和终点均受控；前 7 步启用 | ![rk2_auto](assets/369ad27a02a7a637f973.jpg)<br>**编辑 2 / 保存 1** | ![rk2_gt](assets/541b5bcf59cfafdd863a.jpg)<br>**编辑 2 / 保存 1** |
| **RK2 · N=15**<br>中点和终点均受控；全部 15 步启用 | ![rk2_n15_auto](assets/ff2f2374c373d19f4b96.jpg)<br>**编辑 2 / 保存 2** | ![rk2_n15_gt](assets/4c6002b892695a95eb8d.jpg)<br>**编辑 2 / 保存 2** |

[返回案例索引](#案例索引)


---

<a id="synth_0024"></a>
## synth_0024：hair → Curley

**原始描述：** A Portrait of girl at a mountain

**目标描述：** A Portrait of girl with Curley hair at a mountain

**预期范围变化：** 扩张

### 原图与控制区域

| 原始输入图片 | 自动 mask | GT mask |
| --- | --- | --- |
| ![Source](assets/78197835ff6884766bce.png) | ![Automatic mask](assets/synth_0024_auto_control_mask.png) | ![GT control mask](assets/synth_0024_gt_control_mask.png) |

白色＝允许编辑，黑色＝受保护区域。两张 mask 均为运行配置指定的实际输入，未平滑或额外扩张。

### 生成结果：固定左右列

| 控制方法与时长 | 使用自动 mask | 使用 GT mask |
| --- | --- | --- |
| **Endpoint · N=7**<br>每步更新完成后，约束 mask 外部；前 7 步启用 | ![endpoint_auto](assets/002c031c82c112dde543.jpg)<br>**编辑 2 / 保存 2** | ![endpoint_gt](assets/ae77a3f807d2e1deee34.jpg)<br>**编辑 2 / 保存 2** |
| **RK2 · N=7**<br>中点和终点均受控；前 7 步启用 | ![rk2_auto](assets/7e5813e9923586268372.jpg)<br>**编辑 2 / 保存 2** | ![rk2_gt](assets/9d192821f9be1e344f73.jpg)<br>**编辑 2 / 保存 2** |
| **RK2 · N=15**<br>中点和终点均受控；全部 15 步启用 | ![rk2_n15_auto](assets/7e614a99eb4f1296bcd5.jpg)<br>**编辑 2 / 保存 2** | ![rk2_n15_gt](assets/54dc661264e9a67e5a0e.jpg)<br>**编辑 2 / 保存 2** |

[返回案例索引](#案例索引)


---

<a id="synth_0025"></a>
## synth_0025：hair → Botticelli-Curls

**原始描述：** A Portrait of boy at a street

**目标描述：** A Portrait of boy with Botticelli-Curls hair at a street

**预期范围变化：** 基本不变

### 原图与控制区域

| 原始输入图片 | 自动 mask | GT mask |
| --- | --- | --- |
| ![Source](assets/6be19916a6dc9c8d0526.png) | ![Automatic mask](assets/synth_0025_auto_control_mask.png) | ![GT control mask](assets/synth_0025_gt_control_mask.png) |

白色＝允许编辑，黑色＝受保护区域。两张 mask 均为运行配置指定的实际输入，未平滑或额外扩张。

### 生成结果：固定左右列

| 控制方法与时长 | 使用自动 mask | 使用 GT mask |
| --- | --- | --- |
| **Endpoint · N=7**<br>每步更新完成后，约束 mask 外部；前 7 步启用 | ![endpoint_auto](assets/64fc377e5ab0adc30352.jpg)<br>**编辑 2 / 保存 2** | ![endpoint_gt](assets/dbf432c24cd606be529d.jpg)<br>**编辑 2 / 保存 2** |
| **RK2 · N=7**<br>中点和终点均受控；前 7 步启用 | ![rk2_auto](assets/9e7bf5358aa9378681b9.jpg)<br>**编辑 2 / 保存 2** | ![rk2_gt](assets/85971ec7d9602113bc22.jpg)<br>**编辑 2 / 保存 2** |
| **RK2 · N=15**<br>中点和终点均受控；全部 15 步启用 | ![rk2_n15_auto](assets/c7ae0dbb6b57e2a59640.jpg)<br>**编辑 2 / 保存 2** | ![rk2_n15_gt](assets/f08362727683ea5f50a0.jpg)<br>**编辑 2 / 保存 2** |

[返回案例索引](#案例索引)


---

<a id="synth_0026"></a>
## synth_0026：hair → Curls

**原始描述：** A Portrait of man at a house

**目标描述：** A Portrait of man with Curls hair at a house

**预期范围变化：** 扩张

### 原图与控制区域

| 原始输入图片 | 自动 mask | GT mask |
| --- | --- | --- |
| ![Source](assets/a418e14d71a17e9c5fd9.png) | ![Automatic mask](assets/synth_0026_auto_control_mask.png) | ![GT control mask](assets/synth_0026_gt_control_mask.png) |

白色＝允许编辑，黑色＝受保护区域。两张 mask 均为运行配置指定的实际输入，未平滑或额外扩张。

### 生成结果：固定左右列

| 控制方法与时长 | 使用自动 mask | 使用 GT mask |
| --- | --- | --- |
| **Endpoint · N=7**<br>每步更新完成后，约束 mask 外部；前 7 步启用 | ![endpoint_auto](assets/05efe80372b07745ae79.jpg)<br>**编辑 2 / 保存 1** | ![endpoint_gt](assets/5c06ba1e323c6fce67be.jpg)<br>**编辑 1 / 保存 1** |
| **RK2 · N=7**<br>中点和终点均受控；前 7 步启用 | ![rk2_auto](assets/f1af3de5c19cd949d715.jpg)<br>**编辑 2 / 保存 1** | ![rk2_gt](assets/8018f90134e480293144.jpg)<br>**编辑 2 / 保存 1** |
| **RK2 · N=15**<br>中点和终点均受控；全部 15 步启用 | ![rk2_n15_auto](assets/db51e0a551b9a8978da1.jpg)<br>**编辑 2 / 保存 2** | ![rk2_n15_gt](assets/5c88072254c90f8980fe.jpg)<br>**编辑 0 / 保存 2** |

[返回案例索引](#案例索引)


---

<a id="synth_0027"></a>
## synth_0027：hair → Curls

**原始描述：** A Portrait of woman at a school

**目标描述：** A Portrait of woman with Curls hair at a school

**预期范围变化：** 基本不变

### 原图与控制区域

| 原始输入图片 | 自动 mask | GT mask |
| --- | --- | --- |
| ![Source](assets/d42f9f48f9669efe0304.png) | ![Automatic mask](assets/synth_0027_auto_control_mask.png) | ![GT control mask](assets/synth_0027_gt_control_mask.png) |

白色＝允许编辑，黑色＝受保护区域。两张 mask 均为运行配置指定的实际输入，未平滑或额外扩张。

### 生成结果：固定左右列

| 控制方法与时长 | 使用自动 mask | 使用 GT mask |
| --- | --- | --- |
| **Endpoint · N=7**<br>每步更新完成后，约束 mask 外部；前 7 步启用 | ![endpoint_auto](assets/fbef9afbcab16a31ea7d.jpg)<br>**编辑 2 / 保存 2** | ![endpoint_gt](assets/066ff1de0e529896d1eb.jpg)<br>**编辑 2 / 保存 2** |
| **RK2 · N=7**<br>中点和终点均受控；前 7 步启用 | ![rk2_auto](assets/379fac52db743455c50e.jpg)<br>**编辑 2 / 保存 1** | ![rk2_gt](assets/b3fcbbb6599b66bd0fb5.jpg)<br>**编辑 2 / 保存 1** |
| **RK2 · N=15**<br>中点和终点均受控；全部 15 步启用 | ![rk2_n15_auto](assets/f69a8bbfc8a6ead6934a.jpg)<br>**编辑 2 / 保存 2** | ![rk2_n15_gt](assets/7a93849069c6ae977b41.jpg)<br>**编辑 2 / 保存 2** |

[返回案例索引](#案例索引)


---

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

[返回案例索引](#案例索引)


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

[返回案例索引](#案例索引)


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

[返回案例索引](#案例索引)


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

[返回案例索引](#案例索引)


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

[返回案例索引](#案例索引)


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

[返回案例索引](#案例索引)


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

[返回案例索引](#案例索引)


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

[返回案例索引](#案例索引)


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

[返回案例索引](#案例索引)


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

[返回案例索引](#案例索引)


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

[返回案例索引](#案例索引)


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

[返回案例索引](#案例索引)


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

[返回案例索引](#案例索引)


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

[返回案例索引](#案例索引)


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

[返回案例索引](#案例索引)


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

[返回案例索引](#案例索引)


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

[返回案例索引](#案例索引)


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

[返回案例索引](#案例索引)


---

<a id="synth_0046"></a>
## synth_0046：car body → armored

**原始描述：** A luxury-car at a mountain road

**目标描述：** A luxury-car with armored car body at a mountain road

**预期范围变化：** 基本不变

### 原图与控制区域

| 原始输入图片 | 自动 mask | GT mask |
| --- | --- | --- |
| ![Source](assets/cce9d8228a58e18fd8d8.png) | ![Automatic mask](assets/synth_0046_auto_control_mask.png) | ![GT control mask](assets/synth_0046_gt_control_mask.png) |

白色＝允许编辑，黑色＝受保护区域。两张 mask 均为运行配置指定的实际输入，未平滑或额外扩张。

### 生成结果：固定左右列

| 控制方法与时长 | 使用自动 mask | 使用 GT mask |
| --- | --- | --- |
| **Endpoint · N=7**<br>每步更新完成后，约束 mask 外部；前 7 步启用 | ![endpoint_auto](assets/c8515ffdb63f025a050b.jpg)<br>**编辑 0 / 保存 1** | ![endpoint_gt](assets/8170be0779e8001d7eaa.jpg)<br>**编辑 0 / 保存 1** |
| **RK2 · N=7**<br>中点和终点均受控；前 7 步启用 | ![rk2_auto](assets/0bb3c1e1232cbede7b0e.jpg)<br>**编辑 0 / 保存 1** | ![rk2_gt](assets/2bea26f32454f1398032.jpg)<br>**编辑 0 / 保存 1** |
| **RK2 · N=15**<br>中点和终点均受控；全部 15 步启用 | ![rk2_n15_auto](assets/afe9b00780d7e56bd2ca.jpg)<br>**编辑 0 / 保存 2** | ![rk2_n15_gt](assets/2a8bcf86a19c90ae1c19.jpg)<br>**编辑 0 / 保存 2** |

[返回案例索引](#案例索引)


---

<a id="synth_0047"></a>
## synth_0047：car body → futuristic

**原始描述：** A sedan at a parking lot

**目标描述：** A sedan with futuristic car body at a parking lot

**预期范围变化：** 基本不变

### 原图与控制区域

| 原始输入图片 | 自动 mask | GT mask |
| --- | --- | --- |
| ![Source](assets/d124ca8bebee817fcf00.png) | ![Automatic mask](assets/synth_0047_auto_control_mask.png) | ![GT control mask](assets/synth_0047_gt_control_mask.png) |

白色＝允许编辑，黑色＝受保护区域。两张 mask 均为运行配置指定的实际输入，未平滑或额外扩张。

### 生成结果：固定左右列

| 控制方法与时长 | 使用自动 mask | 使用 GT mask |
| --- | --- | --- |
| **Endpoint · N=7**<br>每步更新完成后，约束 mask 外部；前 7 步启用 | ![endpoint_auto](assets/9b0842bea0b2dad6b4f0.jpg)<br>**编辑 2 / 保存 0** | ![endpoint_gt](assets/255cd47170452fd49391.jpg)<br>**编辑 2 / 保存 2** |
| **RK2 · N=7**<br>中点和终点均受控；前 7 步启用 | ![rk2_auto](assets/80859beadd8d1469ac77.jpg)<br>**编辑 2 / 保存 0** | ![rk2_gt](assets/ff85278f376490e7a336.jpg)<br>**编辑 2 / 保存 2** |
| **RK2 · N=15**<br>中点和终点均受控；全部 15 步启用 | ![rk2_n15_auto](assets/26d75596651b28821b93.jpg)<br>**编辑 2 / 保存 1** | ![rk2_n15_gt](assets/e5f82aa004e4b9782bd6.jpg)<br>**编辑 2 / 保存 2** |

[返回案例索引](#案例索引)


---

<a id="synth_0048"></a>
## synth_0048：car body → rusted

**原始描述：** A classic-car at a suburban road

**目标描述：** A classic-car with rusted car body at a suburban road

**预期范围变化：** 基本不变

### 原图与控制区域

| 原始输入图片 | 自动 mask | GT mask |
| --- | --- | --- |
| ![Source](assets/e388d185668f884a8d08.png) | ![Automatic mask](assets/synth_0048_auto_control_mask.png) | ![GT control mask](assets/synth_0048_gt_control_mask.png) |

白色＝允许编辑，黑色＝受保护区域。两张 mask 均为运行配置指定的实际输入，未平滑或额外扩张。

### 生成结果：固定左右列

| 控制方法与时长 | 使用自动 mask | 使用 GT mask |
| --- | --- | --- |
| **Endpoint · N=7**<br>每步更新完成后，约束 mask 外部；前 7 步启用 | ![endpoint_auto](assets/7b875ff81f3045c3893c.jpg)<br>**编辑 2 / 保存 1** | ![endpoint_gt](assets/a93acaef50461288ae28.jpg)<br>**编辑 2 / 保存 1** |
| **RK2 · N=7**<br>中点和终点均受控；前 7 步启用 | ![rk2_auto](assets/48711e7a5b7d8c65a9e8.jpg)<br>**编辑 2 / 保存 1** | ![rk2_gt](assets/98951f8c34604e4925e8.jpg)<br>**编辑 2 / 保存 1** |
| **RK2 · N=15**<br>中点和终点均受控；全部 15 步启用 | ![rk2_n15_auto](assets/44dcac39deeff6c4a72f.jpg)<br>**编辑 2 / 保存 1** | ![rk2_n15_gt](assets/6215a9281e05de3a15ff.jpg)<br>**编辑 2 / 保存 1** |

[返回案例索引](#案例索引)


---

<a id="synth_0049"></a>
## synth_0049：car body → neon-lit

**原始描述：** A classic-car at a suburban road

**目标描述：** A classic-car with neon-lit car body at a suburban road

**预期范围变化：** 基本不变

### 原图与控制区域

| 原始输入图片 | 自动 mask | GT mask |
| --- | --- | --- |
| ![Source](assets/44c002f36a55477261ee.png) | ![Automatic mask](assets/synth_0049_auto_control_mask.png) | ![GT control mask](assets/synth_0049_gt_control_mask.png) |

白色＝允许编辑，黑色＝受保护区域。两张 mask 均为运行配置指定的实际输入，未平滑或额外扩张。

### 生成结果：固定左右列

| 控制方法与时长 | 使用自动 mask | 使用 GT mask |
| --- | --- | --- |
| **Endpoint · N=7**<br>每步更新完成后，约束 mask 外部；前 7 步启用 | ![endpoint_auto](assets/cf30360a66abbc5f6997.jpg)<br>**编辑 2 / 保存 1** | ![endpoint_gt](assets/64a786c39edd04d29cab.jpg)<br>**编辑 2 / 保存 2** |
| **RK2 · N=7**<br>中点和终点均受控；前 7 步启用 | ![rk2_auto](assets/83743c1040eeae7bb551.jpg)<br>**编辑 2 / 保存 1** | ![rk2_gt](assets/5b0425dede203bfaa4be.jpg)<br>**编辑 2 / 保存 1** |
| **RK2 · N=15**<br>中点和终点均受控；全部 15 步启用 | ![rk2_n15_auto](assets/0742cb11de59bdcc2525.jpg)<br>**编辑 2 / 保存 2** | ![rk2_n15_gt](assets/42e8960fd73b9b0025b2.jpg)<br>**编辑 2 / 保存 2** |

[返回案例索引](#案例索引)


---

<a id="synth_0050"></a>
## synth_0050：car hood → black

**原始描述：** A racing-car at a highway

**目标描述：** A racing-car with black car hood at a highway

**预期范围变化：** 基本不变

### 原图与控制区域

| 原始输入图片 | 自动 mask | GT mask |
| --- | --- | --- |
| ![Source](assets/dbab9da94e3457531e2f.png) | ![Automatic mask](assets/synth_0050_auto_control_mask.png) | ![GT control mask](assets/synth_0050_gt_control_mask.png) |

白色＝允许编辑，黑色＝受保护区域。两张 mask 均为运行配置指定的实际输入，未平滑或额外扩张。

### 生成结果：固定左右列

| 控制方法与时长 | 使用自动 mask | 使用 GT mask |
| --- | --- | --- |
| **Endpoint · N=7**<br>每步更新完成后，约束 mask 外部；前 7 步启用 | ![endpoint_auto](assets/e878bc4e07a8759d64a7.jpg)<br>**编辑 2 / 保存 1** | ![endpoint_gt](assets/9e78ef1aceaa202d5326.jpg)<br>**编辑 2 / 保存 1** |
| **RK2 · N=7**<br>中点和终点均受控；前 7 步启用 | ![rk2_auto](assets/a9aa878ada5dfefb79bf.jpg)<br>**编辑 2 / 保存 1** | ![rk2_gt](assets/462744c9aad3b8f232ea.jpg)<br>**编辑 2 / 保存 2** |
| **RK2 · N=15**<br>中点和终点均受控；全部 15 步启用 | ![rk2_n15_auto](assets/d885895c734b373a0669.jpg)<br>**编辑 2 / 保存 1** | ![rk2_n15_gt](assets/4e1818b4317795ce4e73.jpg)<br>**编辑 2 / 保存 2** |

[返回案例索引](#案例索引)


---

<a id="synth_0051"></a>
## synth_0051：car hood → vinyl-art

**原始描述：** A classic-car at a garage

**目标描述：** A classic-car with vinyl-art car hood at a garage

**预期范围变化：** 基本不变

### 原图与控制区域

| 原始输入图片 | 自动 mask | GT mask |
| --- | --- | --- |
| ![Source](assets/9dd9e40c5761d69234cc.png) | ![Automatic mask](assets/synth_0051_auto_control_mask.png) | ![GT control mask](assets/synth_0051_gt_control_mask.png) |

白色＝允许编辑，黑色＝受保护区域。两张 mask 均为运行配置指定的实际输入，未平滑或额外扩张。

### 生成结果：固定左右列

| 控制方法与时长 | 使用自动 mask | 使用 GT mask |
| --- | --- | --- |
| **Endpoint · N=7**<br>每步更新完成后，约束 mask 外部；前 7 步启用 | ![endpoint_auto](assets/a6cd061aca6828012f33.jpg)<br>**编辑 2 / 保存 0** | ![endpoint_gt](assets/fa9d4b6f336e399704cd.jpg)<br>**编辑 2 / 保存 1** |
| **RK2 · N=7**<br>中点和终点均受控；前 7 步启用 | ![rk2_auto](assets/8a5d9f386f87db25c3fb.jpg)<br>**编辑 2 / 保存 1** | ![rk2_gt](assets/7f17c0119b12a1ffa733.jpg)<br>**编辑 2 / 保存 2** |
| **RK2 · N=15**<br>中点和终点均受控；全部 15 步启用 | ![rk2_n15_auto](assets/a472dacb44ba3acd50b4.jpg)<br>**编辑 1 / 保存 0** | ![rk2_n15_gt](assets/72dbe13d917ee030a236.jpg)<br>**编辑 2 / 保存 2** |

[返回案例索引](#案例索引)


---

<a id="synth_0052"></a>
## synth_0052：car hood → Digital-Camouflage

**原始描述：** A full front facing view of racing car at a parking lot

**目标描述：** A full front facing view of racing car with Digital-Camouflage car hood at a parking lot

**预期范围变化：** 基本不变

### 原图与控制区域

| 原始输入图片 | 自动 mask | GT mask |
| --- | --- | --- |
| ![Source](assets/0a550d7200e6d5926581.png) | ![Automatic mask](assets/synth_0052_auto_control_mask.png) | ![GT control mask](assets/synth_0052_gt_control_mask.png) |

白色＝允许编辑，黑色＝受保护区域。两张 mask 均为运行配置指定的实际输入，未平滑或额外扩张。

### 生成结果：固定左右列

| 控制方法与时长 | 使用自动 mask | 使用 GT mask |
| --- | --- | --- |
| **Endpoint · N=7**<br>每步更新完成后，约束 mask 外部；前 7 步启用 | ![endpoint_auto](assets/2fb88a1be8481b434005.jpg)<br>**编辑 2 / 保存 1** | ![endpoint_gt](assets/ebf1139aa970d637e8fb.jpg)<br>**编辑 2 / 保存 2** |
| **RK2 · N=7**<br>中点和终点均受控；前 7 步启用 | ![rk2_auto](assets/3c61590f881cbdec517a.jpg)<br>**编辑 2 / 保存 2** | ![rk2_gt](assets/82a55bf1590b2134ad93.jpg)<br>**编辑 2 / 保存 2** |
| **RK2 · N=15**<br>中点和终点均受控；全部 15 步启用 | ![rk2_n15_auto](assets/6b5f1392f3ed26e7e3b8.jpg)<br>**编辑 2 / 保存 2** | ![rk2_n15_gt](assets/49a4ca00f3c7e61cf4dc.jpg)<br>**编辑 2 / 保存 2** |

[返回案例索引](#案例索引)


---

<a id="synth_0053"></a>
## synth_0053：car hood → Destroyed

**原始描述：** A full front facing view of BMW car at a parking lot

**目标描述：** A full front facing view of BMW car with Destroyed car hood at a parking lot

**预期范围变化：** 基本不变

### 原图与控制区域

| 原始输入图片 | 自动 mask | GT mask |
| --- | --- | --- |
| ![Source](assets/fba9a260ae813330458d.png) | ![Automatic mask](assets/synth_0053_auto_control_mask.png) | ![GT control mask](assets/synth_0053_gt_control_mask.png) |

白色＝允许编辑，黑色＝受保护区域。两张 mask 均为运行配置指定的实际输入，未平滑或额外扩张。

### 生成结果：固定左右列

| 控制方法与时长 | 使用自动 mask | 使用 GT mask |
| --- | --- | --- |
| **Endpoint · N=7**<br>每步更新完成后，约束 mask 外部；前 7 步启用 | ![endpoint_auto](assets/ad1d51e8210427a4351f.jpg)<br>**编辑 2 / 保存 1** | ![endpoint_gt](assets/532656350bae74992754.jpg)<br>**编辑 2 / 保存 1** |
| **RK2 · N=7**<br>中点和终点均受控；前 7 步启用 | ![rk2_auto](assets/dacaeec996fa60841e21.jpg)<br>**编辑 0 / 保存 1** | ![rk2_gt](assets/5924a356e65d33c0383c.jpg)<br>**编辑 1 / 保存 1** |
| **RK2 · N=15**<br>中点和终点均受控；全部 15 步启用 | ![rk2_n15_auto](assets/aaa6b9387222f5543f81.jpg)<br>**编辑 0 / 保存 2** | ![rk2_n15_gt](assets/4f5d7d5b8dc6ada7986c.jpg)<br>**编辑 2 / 保存 2** |

[返回案例索引](#案例索引)


---

<a id="synth_0054"></a>
## synth_0054：car hood → Rusty

**原始描述：** A full front facing view of Porsche car at a road

**目标描述：** A full front facing view of Porsche car with Rusty car hood at a road

**预期范围变化：** 基本不变

### 原图与控制区域

| 原始输入图片 | 自动 mask | GT mask |
| --- | --- | --- |
| ![Source](assets/46405f16a651cd3e6a71.png) | ![Automatic mask](assets/synth_0054_auto_control_mask.png) | ![GT control mask](assets/synth_0054_gt_control_mask.png) |

白色＝允许编辑，黑色＝受保护区域。两张 mask 均为运行配置指定的实际输入，未平滑或额外扩张。

### 生成结果：固定左右列

| 控制方法与时长 | 使用自动 mask | 使用 GT mask |
| --- | --- | --- |
| **Endpoint · N=7**<br>每步更新完成后，约束 mask 外部；前 7 步启用 | ![endpoint_auto](assets/e3ff3af5989f539a509e.jpg)<br>**编辑 1 / 保存 1** | ![endpoint_gt](assets/5bd245094b4d6be5fcb5.jpg)<br>**编辑 2 / 保存 1** |
| **RK2 · N=7**<br>中点和终点均受控；前 7 步启用 | ![rk2_auto](assets/80b2ad9377f259ae47dd.jpg)<br>**编辑 1 / 保存 1** | ![rk2_gt](assets/669aa642a7c64fd7b0a2.jpg)<br>**编辑 2 / 保存 1** |
| **RK2 · N=15**<br>中点和终点均受控；全部 15 步启用 | ![rk2_n15_auto](assets/ce2ed28d6b0b05ea8fcb.jpg)<br>**编辑 1 / 保存 1** | ![rk2_n15_gt](assets/57104603c78167ceb5f6.jpg)<br>**编辑 2 / 保存 2** |

[返回案例索引](#案例索引)


---

<a id="synth_0055"></a>
## synth_0055：car hood → Graffiti

**原始描述：** A full front facing view of Toyota car at a parking lot

**目标描述：** A full front facing view of Toyota car with Graffiti car hood at a parking lot

**预期范围变化：** 基本不变

### 原图与控制区域

| 原始输入图片 | 自动 mask | GT mask |
| --- | --- | --- |
| ![Source](assets/0bcae518d5ba9c717ade.png) | ![Automatic mask](assets/synth_0055_auto_control_mask.png) | ![GT control mask](assets/synth_0055_gt_control_mask.png) |

白色＝允许编辑，黑色＝受保护区域。两张 mask 均为运行配置指定的实际输入，未平滑或额外扩张。

### 生成结果：固定左右列

| 控制方法与时长 | 使用自动 mask | 使用 GT mask |
| --- | --- | --- |
| **Endpoint · N=7**<br>每步更新完成后，约束 mask 外部；前 7 步启用 | ![endpoint_auto](assets/e51d5587b609a9a21922.jpg)<br>**编辑 2 / 保存 1** | ![endpoint_gt](assets/844078f823cfe6f50384.jpg)<br>**编辑 2 / 保存 1** |
| **RK2 · N=7**<br>中点和终点均受控；前 7 步启用 | ![rk2_auto](assets/316d5477e2ab7023361c.jpg)<br>**编辑 2 / 保存 1** | ![rk2_gt](assets/5b5ee29361916ca81b0f.jpg)<br>**编辑 2 / 保存 1** |
| **RK2 · N=15**<br>中点和终点均受控；全部 15 步启用 | ![rk2_n15_auto](assets/b48222f52e5706bb509f.jpg)<br>**编辑 2 / 保存 2** | ![rk2_n15_gt](assets/0b861e700f1703c386c5.jpg)<br>**编辑 2 / 保存 2** |

[返回案例索引](#案例索引)


---

<a id="synth_0056"></a>
## synth_0056：seat → fabric

**原始描述：** A closeup leather chair at a apartment

**目标描述：** A closeup leather chair with fabric seat at a apartment

**预期范围变化：** 基本不变

### 原图与控制区域

| 原始输入图片 | 自动 mask | GT mask |
| --- | --- | --- |
| ![Source](assets/0255afe3f1b539a20b7f.png) | ![Automatic mask](assets/synth_0056_auto_control_mask.png) | ![GT control mask](assets/synth_0056_gt_control_mask.png) |

白色＝允许编辑，黑色＝受保护区域。两张 mask 均为运行配置指定的实际输入，未平滑或额外扩张。

### 生成结果：固定左右列

| 控制方法与时长 | 使用自动 mask | 使用 GT mask |
| --- | --- | --- |
| **Endpoint · N=7**<br>每步更新完成后，约束 mask 外部；前 7 步启用 | ![endpoint_auto](assets/95af19b7385642b23e73.jpg)<br>**编辑 1 / 保存 2** | ![endpoint_gt](assets/b829891ee41c823d1e93.jpg)<br>**编辑 2 / 保存 1** |
| **RK2 · N=7**<br>中点和终点均受控；前 7 步启用 | ![rk2_auto](assets/53c8bcc6be46a3c3ff6b.jpg)<br>**编辑 2 / 保存 2** | ![rk2_gt](assets/89c61402f2681f9a9a3a.jpg)<br>**编辑 2 / 保存 1** |
| **RK2 · N=15**<br>中点和终点均受控；全部 15 步启用 | ![rk2_n15_auto](assets/09dc0f915f338328a9bb.jpg)<br>**编辑 0 / 保存 2** | ![rk2_n15_gt](assets/fc4b8e02aefbe4a9623f.jpg)<br>**编辑 2 / 保存 2** |

[返回案例索引](#案例索引)


---

<a id="synth_0057"></a>
## synth_0057：seat → plastic

**原始描述：** A closeup soft chair at a photo studio

**目标描述：** A closeup soft chair with plastic seat at a photo studio

**预期范围变化：** 基本不变

### 原图与控制区域

| 原始输入图片 | 自动 mask | GT mask |
| --- | --- | --- |
| ![Source](assets/0e379172a6f60bdc06a8.png) | ![Automatic mask](assets/synth_0057_auto_control_mask.png) | ![GT control mask](assets/synth_0057_gt_control_mask.png) |

白色＝允许编辑，黑色＝受保护区域。两张 mask 均为运行配置指定的实际输入，未平滑或额外扩张。

### 生成结果：固定左右列

| 控制方法与时长 | 使用自动 mask | 使用 GT mask |
| --- | --- | --- |
| **Endpoint · N=7**<br>每步更新完成后，约束 mask 外部；前 7 步启用 | ![endpoint_auto](assets/1193af4aaaf9842b0a5e.jpg)<br>**编辑 2 / 保存 1** | ![endpoint_gt](assets/2dcd39c7aeb1bd3da62a.jpg)<br>**编辑 1 / 保存 1** |
| **RK2 · N=7**<br>中点和终点均受控；前 7 步启用 | ![rk2_auto](assets/7488a7956ea003d899f3.jpg)<br>**编辑 2 / 保存 1** | ![rk2_gt](assets/7501a32355a7b9bf020e.jpg)<br>**编辑 1 / 保存 1** |
| **RK2 · N=15**<br>中点和终点均受控；全部 15 步启用 | ![rk2_n15_auto](assets/180c84384d0182647cfa.jpg)<br>**编辑 2 / 保存 1** | ![rk2_n15_gt](assets/11caad830ec26c478011.jpg)<br>**编辑 0 / 保存 2** |

[返回案例索引](#案例索引)


---

<a id="synth_0058"></a>
## synth_0058：seat → rusted

**原始描述：** A closeup folding chair at a classroom

**目标描述：** A closeup folding chair with rusted seat at a classroom

**预期范围变化：** 基本不变

### 原图与控制区域

| 原始输入图片 | 自动 mask | GT mask |
| --- | --- | --- |
| ![Source](assets/322e7164f614f82a5ff4.png) | ![Automatic mask](assets/synth_0058_auto_control_mask.png) | ![GT control mask](assets/synth_0058_gt_control_mask.png) |

白色＝允许编辑，黑色＝受保护区域。两张 mask 均为运行配置指定的实际输入，未平滑或额外扩张。

### 生成结果：固定左右列

| 控制方法与时长 | 使用自动 mask | 使用 GT mask |
| --- | --- | --- |
| **Endpoint · N=7**<br>每步更新完成后，约束 mask 外部；前 7 步启用 | ![endpoint_auto](assets/68060f3ee6ec7b16b017.jpg)<br>**编辑 2 / 保存 2** | ![endpoint_gt](assets/b3168dec538764ee95b7.jpg)<br>**编辑 2 / 保存 2** |
| **RK2 · N=7**<br>中点和终点均受控；前 7 步启用 | ![rk2_auto](assets/da4bdf865e2e433d143a.jpg)<br>**编辑 2 / 保存 2** | ![rk2_gt](assets/44075672cd1a87f6aca9.jpg)<br>**编辑 2 / 保存 2** |
| **RK2 · N=15**<br>中点和终点均受控；全部 15 步启用 | ![rk2_n15_auto](assets/9114461abc6634d45217.jpg)<br>**编辑 1 / 保存 2** | ![rk2_n15_gt](assets/01174fe8b7995666f8f6.jpg)<br>**编辑 1 / 保存 2** |

[返回案例索引](#案例索引)


---

<a id="synth_0059"></a>
## synth_0059：seat → wooden

**原始描述：** A closeup leather chair at a classroom

**目标描述：** A closeup leather chair with wooden seat at a classroom

**预期范围变化：** 基本不变

### 原图与控制区域

| 原始输入图片 | 自动 mask | GT mask |
| --- | --- | --- |
| ![Source](assets/045548f9199b33a12406.png) | ![Automatic mask](assets/synth_0059_auto_control_mask.png) | ![GT control mask](assets/synth_0059_gt_control_mask.png) |

白色＝允许编辑，黑色＝受保护区域。两张 mask 均为运行配置指定的实际输入，未平滑或额外扩张。

### 生成结果：固定左右列

| 控制方法与时长 | 使用自动 mask | 使用 GT mask |
| --- | --- | --- |
| **Endpoint · N=7**<br>每步更新完成后，约束 mask 外部；前 7 步启用 | ![endpoint_auto](assets/6c223a4652ebf8f66273.jpg)<br>**编辑 0 / 保存 2** | ![endpoint_gt](assets/0477ad6bf646e52615e9.jpg)<br>**编辑 0 / 保存 2** |
| **RK2 · N=7**<br>中点和终点均受控；前 7 步启用 | ![rk2_auto](assets/e03ea3842bde0bf5c4b0.jpg)<br>**编辑 0 / 保存 2** | ![rk2_gt](assets/4c97a1b23d57ea52ae1c.jpg)<br>**编辑 0 / 保存 2** |
| **RK2 · N=15**<br>中点和终点均受控；全部 15 步启用 | ![rk2_n15_auto](assets/c44081434bbca937b4ee.jpg)<br>**编辑 0 / 保存 2** | ![rk2_n15_gt](assets/abc9ca68da5a561cc5d3.jpg)<br>**编辑 0 / 保存 2** |

[返回案例索引](#案例索引)
