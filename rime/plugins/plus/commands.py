#!/usr/bin/python
#
# Copyright (c) 2015 Rime Project.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#

import itertools
import os
import os.path
from subprocess import call

import rime.basic.targets.problem   # target dependency
import rime.basic.targets.project   # target dependency
import rime.basic.targets.solution  # target dependency
import rime.basic.targets.testset   # target dependency
from rime.basic import commands as basic_commands
from rime.basic import consts
from rime.core import commands
from rime.core import taskgraph
from rime.core import targets
from rime.util import class_registry
from rime.util import files

class PackerBase(object):
  @taskgraph.task_method
  def Pack(self, ui, testset):
    raise NotImplementedError()

class UploaderBase(object):
  @taskgraph.task_method
  def Upload(self, ui, problem, dryrun):
    raise NotImplementedError()

class SubmitterBase(object):
  @taskgraph.task_method
  def Submit(self, ui, solution):
    raise NotImplementedError()

packer_registry = class_registry.ClassRegistry(PackerBase)
uploader_registry = class_registry.ClassRegistry(UploaderBase)
submitter_registry = class_registry.ClassRegistry(SubmitterBase)

def EditFile(filename, initial):
  EDITOR = os.environ.get('EDITOR','vi')
  files.WriteFile(initial, filename)
  call([EDITOR, filename])

class Project(targets.registry.Project):

  @taskgraph.task_method
  def Pack(self, ui):
    results = yield taskgraph.TaskBranch(
      [problem.Pack(ui) for problem in self.problems])
    yield all(results)

  @taskgraph.task_method
  def Upload(self, ui):
    results = yield taskgraph.TaskBranch(
      [problem.Upload(ui) for problem in self.problems])
    yield all(results)

  @taskgraph.task_method
  def Submit(self, ui):
    results = yield taskgraph.TaskBranch(
      [problem.Submit(ui) for problem in self.problems])
    yield all(results)

  @taskgraph.task_method
  def Add(self, args, ui):
    if len(args) != 2:
      yield None
    ttype = args[0].lower()
    name = args[1]
    if ttype == 'problem':
      content = '''\
# -*- coding: utf-8; mode: python -*-

pid='X'

problem(
  time_limit=1.0,
  id=pid,
  title=pid + ": Your Problem Name",
  #wiki_name="Your pukiwiki page name", # for wikify plugin
  #assignees=['Assignees', 'for', 'this', 'problem'], # for wikify plugin
  #need_custom_judge=True, # for wikify plugin
  #reference_solution='???',
  )

atcoder_config(
  task_id=-1 # None means a spare
)
'''
      newdir = os.path.join(self.base_dir, name)
      if(os.path.exists(newdir)):
        ui.errors.Error(self, "{0} already exists.".format(newdir))
        yield None
      os.makedirs(newdir)
      EditFile(os.path.join(newdir, 'PROBLEM'), content)
      ui.console.PrintAction('ADD', None, '%s/PROBLEM' % newdir)
    else:
      ui.errors.Error(self, "Target type {0} cannot be put here.".format(ttype))
      yield None

class Problem(targets.registry.Problem):

  @taskgraph.task_method
  def Pack(self, ui):
    results = yield taskgraph.TaskBranch(
      [testset.Pack(ui) for testset in self.testsets])
    yield all(results)

  @taskgraph.task_method
  def Upload(self, ui):
    if not (yield self.Pack(ui)):
      yield False
    if len(uploader_registry.classes) > 0:
      results = yield taskgraph.TaskBranch(
        [uploader().Upload(ui, self, not ui.options.upload) for uploader 
          in uploader_registry.classes.values()])
      yield all(results)
    else:
      ui.errors.Error(self, "Upload nothing: you must add some plugin.")
      yield False

  @taskgraph.task_method
  def Submit(self, ui):
    results = yield taskgraph.TaskBranch(
      [solution.Submit(ui) for solution in self.solutions])
    yield all(results)

  @taskgraph.task_method
  def Add(self, args, ui):
    if len(args) != 2:
      yield None
    ttype = args[0].lower()
    name = args[1]
    if ttype == 'solution':
      content = '''\
# -*- coding: utf-8; mode: python -*-

## Solution
#c_solution(src='main.c') # -lm -O2 as default
#cxx_solution(src='main.cc', flags=[]) # -std=c++11 -O2 as default
#java_solution(src='Main.java', encoding='UTF-8', mainclass='Main')
#java_solution(src='Main.java', encoding='UTF-8', mainclass='Main', challenge_cases=[])
#java_solution(src='Main.java', encoding='UTF-8', mainclass='Main', challenge_cases=['10_corner*.in'])
#script_solution(src='main.sh') # shebang line is required
#script_solution(src='main.pl') # shebang line is required 
#script_solution(src='main.py') # shebang line is required
#script_solution(src='main.rb') # shebang line is required
#js_solution(src='main.js') # javascript (nodejs) 
#hs_solution(src='main.hs') # haskell (stack + ghc)
#cs_solution(src='main.cs') # C# (mono)

## Score
#expected_score(100)
'''
      newdir = os.path.join(self.base_dir, name)
      if(os.path.exists(newdir)):
        ui.errors.Error(self, "{0} already exists.".format(newdir))
        yield None
      os.makedirs(newdir)
      EditFile(os.path.join(newdir, 'SOLUTION'), content)
      ui.console.PrintAction('ADD', None, '%s/SOLUTION' % newdir)
    elif ttype == 'testset':
      content = '''\
# -*- coding: utf-8; mode: python -*-

## Input generators.
#c_generator(src='generator.c')
#cxx_generator(src='generator.cc', dependency=['testlib.h'])
#java_generator(src='Generator.java', encoding='UTF-8', mainclass='Generator')
#script_generator(src='generator.pl')

## Input validators.
#c_validator(src='validator.c')
#cxx_validator(src='validator.cc', dependency=['testlib.h'])
#java_validator(src='Validator.java', encoding='UTF-8', mainclass='tmp/validator/Validator')
#script_validator(src='validator.pl')

## Output judges.
#c_judge(src='judge.c')
#cxx_judge(src='judge.cc', dependency=['testlib.h'], variant=testlib_judge_runner)
#java_judge(src='Judge.java', encoding='UTF-8', mainclass='Judge')
#script_judge(src='judge.py')

## Reactives.
#c_reactive(src='reactive.c')
#cxx_reactive(src='reactive.cc', dependency=['testlib.h', 'reactive.hpp'], variant=kupc_reactive_runner)
#java_reactive(src='Reactive.java', encoding='UTF-8', mainclass='Judge')
#script_reactive(src='reactive.py')

## Extra Testsets.
#icpc_merger(input_terminator='0 0\\n') # icpc type
#icpc_merger(input_terminator='0 0\\n', output_replace=casenum_replace('Case 1', 'Case {{0}}')) # icpc wf ~2011
#gcj_merger(output_replace=casenum_replace('Case 1', 'Case {{0}}'))
id='{0}'
#merged_testset(name=id + '_Merged', input_pattern='*.in')
#subtask_testset(name='All', score=100, input_patterns=['*'])
#scoring_judge() # precisely scored by judge program like Jiyukenkyu (KUPC 2013)
'''
      newdir = os.path.join(self.base_dir, name)
      if(os.path.exists(newdir)):
        ui.errors.Error(self, "{0} already exists.".format(newdir))
        yield None
      os.makedirs(newdir)
      EditFile(os.path.join(newdir, 'TESTSET'), content.format(self.id))
      ui.console.PrintAction('ADD', self, '%s/TESTSET' % newdir)
    else:
      ui.errors.Error(self, "Target type {0} cannot be put here.".format(ttype))
      yield None

class Solution(targets.registry.Solution):
  
  @taskgraph.task_method
  def Pack(self, ui):
    ui.errors.Error(self, "A solution is not a target.")
    yield False

  @taskgraph.task_method
  def Upload(self, ui):
    ui.errors.Error(self, "A solution is not a target.")
    yield False

  @taskgraph.task_method
  def Submit(self, ui):
    if not (yield self.Build(ui)):
      yield False
    if len(submitter_registry.classes) > 0:
      results = yield taskgraph.TaskBranch(
        [submitter().Submit(ui, self) for submitter
          in submitter_registry.classes.values()])
      yield all(results)
    else:
      ui.errors.Error(self, "Submit nothing: you must add some plugin.")
      yield False

class Testset(targets.registry.Testset):

  @taskgraph.task_method
  def Pack(self, ui):
    if not (yield self.Build(ui)):
      yield False
    if len(packer_registry.classes) > 0:
      results = yield taskgraph.TaskBranch(
        [packer().Pack(ui, self) for packer
          in packer_registry.classes.values()])
      yield all(results)
    else:
      ui.errors.Error(self, "Pack nothing: you must add some plugin.")
      yield False

  @taskgraph.task_method
  def Upload(self, ui):
    ui.errors.Error(self, "A testset is not a target.")
    yield False

  @taskgraph.task_method
  def Submit(self, ui):
    ui.errors.Error(self, "A testset is not a target.")
    yield False

targets.registry.Override('Project',  Project)
targets.registry.Override('Problem',  Problem)
targets.registry.Override('Solution', Solution)
targets.registry.Override('Testset',  Testset)

class Pack(commands.CommandBase):
  def __init__(self, parent):
    super(Pack, self).__init__(
      'pack',
      '[<target>]',
      'Pack testsets to export to online judges.',
      '',
      parent)

  def Run(self, project, args, ui):
    return basic_commands.RunCommon('Pack', project, args, ui)

class Upload(commands.CommandBase):
  def __init__(self, parent):
    super(Upload, self).__init__(
      'upload',
      '[<target>]',
      'Upload testsets to export to online judges.',
      '',
      parent)

    self.AddOptionEntry(commands.OptionEntry(
        'u', 'upload', 'upload', bool, False, None,
        'Without this option, just dry-run.'))

  def Run(self, project, args, ui):
    return basic_commands.RunCommon('Upload', project, args, ui)

class Submit(commands.CommandBase):
  def __init__(self, parent):
    super(Submit, self).__init__(
      'submit',
      '[<target>]',
      'Submit solutions to online judges.',
      '',
      parent)

  def Run(self, project, args, ui):
    return basic_commands.RunCommon('Submit', project, args, ui)

commands.registry.Add(Pack)
commands.registry.Add(Upload)
commands.registry.Add(Submit)


def Run(method_name, project, args, ui):
  if args:
    base_dir = os.path.abspath(args[0])
    args = args[1:]
  else:
    base_dir = os.getcwd()

  obj = project.FindByBaseDir(base_dir)
  if not obj:
    ui.errors.Error(None,
                    'Target directory is missing or not managed by Rime.')
    return None

  return getattr(obj, method_name)(args, ui)

class Add(commands.CommandBase):
  def __init__(self, parent):
    super(Add, self).__init__(
      'add',
      '[<parent target> <child type> <child dir>]',
      'Add a new target directory.',
      '',
      parent)

  def Run(self, project, args, ui):
    return Run('Add', project, args, ui)

commands.registry.Add(Add)