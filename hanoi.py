#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, division

from cocos.director import director
from cocos.scene import Scene
from cocos.scenes import *
from cocos.layer import ColorLayer
from cocos.sprite import Sprite
from cocos.text import Label
from cocos.actions import *

import cocos.euclid as eu
import cocos.collision_model as cm


class LaunchLayer(ColorLayer):
    """
    开场动画图层
    """
    is_event_handler = True

    def __init__(self):
        super(LaunchLayer, self).__init__(222, 200, 158, 255)
        sprite = Sprite('hanoi.png')
        w, h = director.get_window_size()
        sprite.position = w/2 - 10, 380

        plate1 = Sprite('plate.jpeg', position=(w/2 - 10, 130))
        plate2 = Sprite('plate.jpeg', position=(w/2 - 10, 195))
        plate3 = Sprite('plate.jpeg', position=(w/2 - 10, 265))
        self.add(sprite)

        plate2.scale_x = 0.8
        plate3.scale_x = 0.6
        self.add(plate1)
        self.add(plate2)
        self.add(plate3)

        # 刚开始的可见度都为0
        sprite.opacity = 0
        plate3.opacity = 0
        plate2.opacity = 0
        plate1.opacity = 0

        plate1.do(AccelDeccel(FadeIn(1.5) | MoveBy((0, -30), duration=1.5)))
        plate2.do(AccelDeccel(Delay(1) + FadeIn(1.5) | MoveBy((0, -30), duration=2.5)))
        plate3.do(AccelDeccel(Delay(2) + FadeIn(1.5) | MoveBy((0, -30), duration=3.5)))

        sprite.do(AccelDeccel(Delay(3) + FadeIn(1.5) | MoveBy((0, -30), duration=4.5)))

        # 这里设置在4秒之后自动开始游戏
        self.schedule_interval(self.start_game, 4)

    def on_key_press(self, k, m):
        self.start_game(None)

    def start_game(self, dt):
        director.replace(FadeTransition(Scene(GameLayer(level=1)), duration=1))


class Actor(Sprite):
    """
    游戏中的元素基类
    """
    def __init__(self, position=(0, 0), rotation=0, scale=1, *args, **kwargs):
        super(Actor, self).__init__('plate.jpeg', position, rotation, scale)
        self.position = eu.Vector2(position[0], position[1])
        if 'scale_x' in kwargs:
            self.scale_x = kwargs['scale_x']
        if rotation == 0:
            self.cshape = cm.AARectShape(self.position, self.width * scale * 0.5, self.height * scale * 0.5)
        elif rotation == 90:
            self.cshape = cm.AARectShape(self.position, self.height * scale * 0.5, self.width * scale * 0.5)


class Plate(Actor):
    """
    盘子
    """
    def __init__(self, scale=1, pillar=None, position=(0, 0), scale_x=0.7):
        super(Plate, self).__init__(scale=scale, position=position, scale_x=scale_x)
        self.pillar = pillar
        self.x = self.pillar.x
        self.y = 67 + (self.height + 5) * (0.7 - scale_x) * 10
        self.position = self.x, self.y
        self.cshape.center = eu.Vector2(self.x, self.y)
        self.cshape.rx = self.width * scale_x * 0.5


class Pillar(Actor):
    """
    柱子
    """
    def __init__(self, position=(0, 0), *args, **kwargs):
        super(Pillar, self).__init__(position=position, rotation=90, *args, **kwargs)

        # 盘子已栈结构存储
        self.plate_stack = []

    def pop_plate(self):
        """
        删除盘子
        """
        self.plate_stack.pop()

    def add_plate(self, plate):
        """
        增加盘子，判断是否合法
        """
        if len(self.plate_stack) == 0 or plate.scale_x < self.plate_stack[-1].scale_x:
                self.plate_stack.append(plate)
                return True
        return False


class GameLayer(ColorLayer):

    is_event_handler = True
    dragging = False
    # 当前选中的盘子
    selected_plate = None

    # 选中盘子的原始位置
    # 当拖动不合法的时候，盘子应该返回到原始位置
    origin_place = None

    step = 0

    def __init__(self, level=3):
        super(GameLayer, self).__init__(222, 200, 158, 255)

        self.level = level
        # 初始化柱子
        self.pillar1 = Pillar(position=(160, 200))
        self.pillar2 = Pillar(position=(400, 200))
        self.pillar3 = Pillar(position=(660, 200))

        self.pillars = [self.pillar1, self.pillar2, self.pillar3]
        self.add(self.pillar1)
        self.add(self.pillar2)
        self.add(self.pillar3)

        # 初始化盘子
        self.init_plates()

        # 初始化HUD
        self.st = Label(
            'Step: 0',
            font_size=24,
            font_name='Comic Sans MS',
            anchor_x='center', anchor_y='center',
        )
        self.st.position = 760, 460

        self.add(self.st)

        self.restart = Sprite('refresh.png', color=(255, 255, 255), scale=0.2)
        self.restart.position = 40, 455
        self.restart.cshape = cm.AARectShape(self.restart.position, self.restart.width * 0.2 * 0.5, self.restart.height * 0.2 * 0.5)
        self.add(self.restart)

        # 初始化碰撞
        w, h = director.get_window_size()
        self.collman = cm.CollisionManagerGrid(0, w, 0, h, self.pillar1.width * 1.25, self.pillar1.height * 1.25)
        self.collman.add(self.pillar1)
        self.collman.add(self.pillar2)
        self.collman.add(self.pillar3)

        # 目前只监听step的更新
        self.schedule(self.update)

    def update(self, dt):
        self.st.element.text = 'Steps: ' + str(self.step)

    def init_plates(self, level=3):
        """
        初始化的时候，先把所有柱子上的盘子清空
        然后再放到第一根柱子上
        """
        self.selected_plate = None
        self.origin_place = None
        self.step = 0

        for plate in self.pillar1.plate_stack:
            plate.kill()
            self.pillar1.plate_stack = []
        for plate in self.pillar2.plate_stack:
            plate.kill()
            self.pillar2.plate_stack = []
        for plate in self.pillar3.plate_stack:
            plate.kill()
            self.pillar3.plate_stack = []

        for l in range(self.level):
            plate = Plate(pillar=self.pillar1, scale_x=(0.7 - 0.1*l))
            self.pillar1.add_plate(plate)
            self.add(plate)

    def on_mouse_press(self, x, y, k, m):

        # 判断是否点击重来
        if self.restart.cshape.touches_point(x, y):
            self.init_plates(self.level)

        # 找到鼠标拖动的盘子
        for pillar in self.pillars:
            if len(pillar.plate_stack) > 0 and pillar.plate_stack[-1].cshape.touches_point(x, y):
                self.selected_plate = pillar.plate_stack[-1]
                self.origin_place = self.selected_plate.position
                break

    def on_mouse_drag(self, x, y, dx, dy, k, m):
        self.dragging = True
        if self.dragging and self.selected_plate is not None:
            # 盘子随鼠标移动
            self.selected_plate.position = x, y

            # 物体位置变动时候，cshape的center并不会自动改变，所以这里要显示更新center
            # 下同
            self.selected_plate.cshape.center = self.selected_plate.position

    def on_mouse_release(self, x, y, k, m):
        self.dragging = False

        if self.selected_plate is None:
            return None
        # 当释放鼠标的时候，检查盘子是否和某个柱子碰撞
        # 这个函数只返回CollisionManager监听（add）了的对象
        obj_set = self.collman.objs_colliding(self.selected_plate)
        if len(obj_set) > 0:
            # 碰到了柱子
            obj = obj_set.pop()
            # 盘子落到柱子上
            # 之前的柱子需要弹出该盘子
            self.selected_plate.pillar.pop_plate()

            # 碰撞的柱子需要增加该盘子
            if obj.add_plate(self.selected_plate):
                last_plate_y = obj.plate_stack[-2].position[1] + self.selected_plate.height + 5 if len(
                    obj.plate_stack) > 1 else 67
                self.selected_plate.position = obj.x, last_plate_y
                self.selected_plate.cshape.center = self.selected_plate.position

                # 当盘子移动到另一个柱子上时，step加1
                if self.selected_plate.pillar != obj:
                    self.step += 1

                # 盘子的主体柱子要更改
                self.selected_plate.pillar = obj

                # 如果所有的盘子，都已经移到第三根柱子上，则为胜利
                if len(self.pillar3.plate_stack) == self.level:
                    if self.level == 4:
                        # 通关
                        director.replace(RotoZoomTransition(Scene(WinLayer()), duration=1))
                    else:
                        # 进入下一关
                        director.replace(FadeTransition(Scene(GameLayer(level=self.level+1)), duration=1))
            else:
                # 如果增加失败，说明不能这样移动
                # 盘子返回原来的位置
                self.selected_plate.position = self.origin_place
                self.selected_plate.cshape.center = self.selected_plate.position
                self.selected_plate.pillar.add_plate(self.selected_plate)
        else:
            self.selected_plate.position = self.origin_place
            self.selected_plate.cshape.center = self.selected_plate.position

        self.selected_plate = None
        self.origin_place = None


class WinLayer(ColorLayer):

    def __init__(self):
        super(WinLayer, self).__init__(222, 200, 158, 255)

        text = Label(
            'You win!',
            font_size=64,
            anchor_x='center', anchor_y='center',

        )
        w, h = director.get_window_size()
        text.position = w / 2, h / 2
        self.add(text)


if __name__ == '__main__':
    director.init(caption='Hanoi by anosann', width=840)
    director.run(Scene(LaunchLayer()))
