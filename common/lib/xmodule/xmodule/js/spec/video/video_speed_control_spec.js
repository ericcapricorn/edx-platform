(function (undefined) {
    describe('VideoSpeedControl', function () {
        var state, oldOTBD;

        beforeEach(function () {
            oldOTBD = window.onTouchBasedDevice;
            window.onTouchBasedDevice = jasmine.createSpy('onTouchBasedDevice')
                .andReturn(null);
        });

        afterEach(function () {
            $('source').remove();
            window.onTouchBasedDevice = oldOTBD;
        });

        describe('constructor', function () {
            describe('always', function () {
                beforeEach(function () {
                    state = jasmine.initializePlayer();
                });

                it('add the video speed control to player', function () {
                    var li, secondaryControls;

                    secondaryControls = $('.secondary-controls');
                    li = secondaryControls.find('.video_speeds li');

                    expect(secondaryControls).toContain('.speeds');
                    expect(secondaryControls).toContain('.video_speeds');
                    expect(secondaryControls.find('p.active').text())
                        .toBe('1.50x');
                    expect(li.filter('.active')).toHaveData(
                        'speed', state.videoSpeedControl.currentSpeed
                    );
                    expect(li.length).toBe(state.videoSpeedControl.speeds.length);

                    $.each(li.toArray().reverse(), function (index, link) {
                        expect($(link)).toHaveData(
                            'speed', state.videoSpeedControl.speeds[index]
                        );
                        expect($(link).find('a').text()).toBe(
                            state.videoSpeedControl.speeds[index] + 'x'
                        );
                    });
                });

                it('add ARIA attributes to speed control', function () {
                    var speedControl = $('div.speeds>a');

                    expect(speedControl).toHaveAttrs({
                        'role': 'button',
                        'title': 'Speeds',
                        'aria-disabled': 'false'
                    });
                });

                it('bind to change video speed link', function () {
                    expect($('.video_speeds a')).toHandleWith(
                        'click', state.videoSpeedControl.changeVideoSpeed
                    );
                });
            });

            describe('when running on touch based device', function () {
                $.each(['iPad', 'Android'], function (index, device) {
                    it('is not rendered on' + device, function () {
                        window.onTouchBasedDevice.andReturn([device]);
                        state = jasmine.initializePlayer();

                        expect(state.el.find('div.speeds')).not.toExist();
                    });
                });
            });

            describe('when running on non-touch based device', function () {
                var keypress = $.Event('keypress'),
                    speedControl = $('div.speeds'),
                    speedEntries = $('div.speeds>a'),
                    firstSpeedEntry = speedEntries.first(),
                    secondSpeedEntry = $(speedEntries.eq(1)),
                    previousLastSpeedEntry = $(speedEntries.eq(speedEntries.length-1)),
                    lastSpeedEntry = speedEntries.last();

                beforeEach(function () {
                    state = jasmine.initializePlayer();
                    spyOnEvent(firstSpeedEntry, 'focus');
                    spyOnEvent(secondSpeedEntry, 'focus');
                    spyOnEvent(previousLastSpeedEntry, 'focus');
                    spyOnEvent(lastSpeedEntry, 'focus');
                });

                it('open the speed toggle on hover', function () {
                    speedControl.mouseenter();
                    expect(speedControl).toHaveClass('open');

                    speedControl.mouseleave();
                    expect(speedControl).not.toHaveClass('open');
                });

                it('close the speed toggle on mouse out', function () {
                    speedControl.mouseenter().mouseleave();

                    expect(speedControl).not.toHaveClass('open');
                });

                it('close the speed toggle on click', function () {
                    speedControl.mouseenter().click();

                    expect(speedControl).not.toHaveClass('open');
                });

                it('open/close the speed toggle on ENTER keydown', function () {
                    keypress.which = $.ui.keyCode.ENTER;
                    speedControl.trigger(keypress);
                    expect(speedControl).toHaveClass('open');
                    speedControl.trigger(keypress);
                    expect(speedControl).not.toHaveClass('open');
                });

                it('open/close the speed toggle on SPACE keydown', function () {
                    keypress.which = $.ui.keyCode.SPACE;
                    speedControl.trigger(keypress);
                    expect(speedControl).toHaveClass('open');
                    speedControl.trigger(keypress);
                    expect(speedControl).not.toHaveClass('open');
                });

                it('open the speed toggle on UP keydown', function () {
                    keypress.which = $.ui.keyCode.UP;
                    speedControl.trigger(keypress);
                    expect(speedControl).toHaveClass('open');
                    expect('focus').toHaveBeenTriggeredOn(lastSpeedEntry);
                });

                it('close the speed toggle on ESC keydown', function () {
                    keypress.which = $.ui.keyCode.ESC;
                    speedControl.trigger(keypress);
                    expect(speedControl).not.toHaveClass('open');
                });

                it('UP and DOWN keydown function as expected', function () {
                    // Iterate through list in both directions and check if
                    // things wrap up correctly.
                    keypress.which = $.ui.keyCode.UP;
                    speedControl.trigger(keypress);
                    lastSpeedEntry.trigger(keypress);
                    expect('focus').toHaveBeenTriggeredOn(previousLastSpeedEntry);
                    keypress.which = $.ui.keyCode.DOWN;
                    previousLastSpeedEntry.trigger(keypress);
                    expect('focus').toHaveBeenTriggeredOn(lastSpeedEntry);
                    lastSpeedEntry.trigger(keypress);
                    expect('focus').toHaveBeenTriggeredOn(firstSpeedEntry);
                    firstSpeedEntry.trigger(keypress);
                    expect('focus').toHaveBeenTriggeredOn(secondSpeedEntry);
                    keypress.which = $.ui.keyCode.UP;
                    secondSpeedEntry.trigger(keypress);
                    expect('focus').toHaveBeenTriggeredOn(firstSpeedEntry);
                    firstSpeedEntry.trigger(keypress);
                    expect('focus').toHaveBeenTriggeredOn(lastSpeedEntry);
                });
            });
        });

        describe('changeVideoSpeed', function () {
            // This is an unnecessary test. The internal browser API, and
            // YouTube API detect (and do not do anything) if there is a
            // request for a speed that is already set.
            //
            //     describe("when new speed is the same") ...

            describe('when new speed is not the same', function () {
                beforeEach(function () {
                    state = jasmine.initializePlayer();
                    state.videoSpeedControl.setSpeed(1.0);
                    spyOn(state.videoPlayer, 'onSpeedChange').andCallThrough();

                    $('li[data-speed="0.75"] a').click();
                });

                it('trigger speedChange event', function () {
                    expect(state.videoPlayer.onSpeedChange).toHaveBeenCalled();
                    expect(state.videoSpeedControl.currentSpeed).toEqual(0.75);
                });
            });

            describe(
                'make sure the speed control gets the focus afterwards',
                function ()
            {
                var anchor;

                beforeEach(function () {
                    state = jasmine.initializePlayer();
                    anchor= $('.speeds > a').first();
                    state.videoSpeedControl.setSpeed(1.0);
                    spyOnEvent(anchor, 'focus');
                });

                it('when the speed is the same', function () {
                    $('li[data-speed="1.0"] a').click();
                    expect('focus').toHaveBeenTriggeredOn(anchor);
                });

                it('when the speed is not the same', function () {
                    $('li[data-speed="0.75"] a').click();
                    expect('focus').toHaveBeenTriggeredOn(anchor);
                });
            });
        });

        describe('onSpeedChange', function () {
            beforeEach(function () {
                state = jasmine.initializePlayer();
                $('li[data-speed="1.0"] a').addClass('active');
                state.videoSpeedControl.setSpeed(0.75);
            });

            it('set the new speed as active', function () {
                expect($('.video_speeds li[data-speed="1.0"]'))
                    .not.toHaveClass('active');
                expect($('.video_speeds li[data-speed="0.75"]'))
                    .toHaveClass('active');
                expect($('.speeds p.active')).toHaveHtml('0.75x');
            });
        });
    });
}).call(this);
