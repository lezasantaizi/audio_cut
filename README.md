# audio_cut
[语音切割](https://zhuanlan.zhihu.com/p/45328164?just_published=2)，python ，webrtc，

## Tips
1. 使用 pydub 读取音频文件
2. 使用 webrtcvad 判断frame是否是speech；
3. agg_value: (0, 1, 2, or 3). 数值越大，判断越是粗略，连着的静音或者响声越多
> vad = webrtcvad.Vad(agg_value)

> is_speech = vad.is_speech(frame.bytes, sample_rate)
4. frame_duration = 30ms 
5. 使用长度为10（= padding_duration_ms ／ frame_duration ）的队列ring_buffer临时保存frame

## 核心函数vad_collector 的关键原理介绍：
* 初始状态：triggered = False，表示不是speech;
* 当ring_buffer中的frame 超过90% 都是speech时，triggered = True，表明从ring_buffer的头部开始，进入speech状态；
* 使用frame 更新ring_buffer, 按照deque的性质，当队列填满时，ring_buffer中比较旧的会自动出队列
* 当ring_buffer中的frame 超过90% 都不是speech时，triggered = False,表明从ring_buffer的尾部结束，退出speech状态；
* 当退出speech时进行这样处理: 从进入speech状态到退出speech状态这期间的所有frame 全部yield ,等外部循环一次处理之后，再次回来vad_collector进行下一轮voiced_frames的收集。
* 最后当frame循环结束之后，别忘了收尾工作


