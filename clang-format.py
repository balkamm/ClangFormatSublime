import sublime, sublime_plugin
import subprocess
import re
import itertools


def get_settings():
  return sublime.load_settings("clangtools.sublime-settings")


def get_setting(key, default=None, view=None):
  if view == None:
    view = sublime.active_window().active_view()

  if view.settings().has("ClangTools"):
    settings = view.settings().get("ClangTools")
    if key in settings:
      return settings[key]

  return get_settings().get(key, default)

def get_cmd(args=[]):
  clang_cmd = get_setting('clang_command', 'clang')
  std = get_setting('std')
  flags = get_setting('flags')
  
  cmd = [clang_cmd,'-x','c++','-fsyntax-only']
  if flags:
    cmd.extend(flags)
  if std:
    cmd.append('-std='+std)
  cmd.extend(args)
  return cmd

class ClangFormatCommand(sublime_plugin.TextCommand):
  def run(self, edit):
    r = sublime.Region(0, self.view.size())
    try:
      clang_cmd = get_setting('format_command', 'clang-format')
      style = get_setting('style')
      cmd = [clang_cmd]
      if style:
        cmd.extend(['--style', style])
      p = subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.PIPE)
      stdoutdata, stderrdata = p.communicate(self.view.substr(r).encode('utf-8'))
      p.stdin.close()
      self.view.replace(edit, r, stdoutdata.decode('utf-8'))

    except subprocess.CalledProcessError as e:
      print(str(e))

  def description(self):
    return "Format: Clang"


# class ClangLintCommand(sublime_plugin.TextCommand):
#   def run(self, edit):
#     print("Clang Linting")
#     try:
#       fname = self.view.file_name()
#       results = ""
#       if fname:
#         cmd = get_cmd(['-fno-caret-diagnostics',
#                        '-fdiagnostics-print-source-range-info',
#                        '-fdiagnostics-parseable-fixits',
#                        fname])
#         print(cmd)
#         p = subprocess.Popen(cmd,stderr=subprocess.PIPE)
#         stdoutdata, stderrdata = p.communicate()
#         results = stderrdata.decode('utf-8')
#         print(results)
#       else:
#         cmd = get_cmd(['-fno-caret-diagnostics',
#                        '-fdiagnostics-print-source-range-info',
#                        '-fdiagnostics-parseable-fixits'])

#         p = subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.PIPE)
#         r = sublime.Region(0, self.view.size())
#         stdoutdata, stderrdata = p.communicate(self.view.substr(r).encode('utf-8'))
#         results = stdoutdata.decode('utf-8')

#       rows = results.splitlines()
#       warnings=[]
#       errors=[]
#       for row in rows:
#         if row[:21] == 'In file included from':
#           continue

#         err = re.match("^(?P<filename>[^:]*):(?P<line>[0-9]*):(?P<col>[0-9]*):(?P<range>{(?P<from_line>[0-9]*):(?P<from_col>[0-9]*)-(?P<to_line>[0-9]*):(?P<to_col>[0-9]*)}:)? (?P<type>(warning)|(error)|(fatal error)):(?P<msg>.*)$",row)
#         filename = err.group('filename')
#         if filename != self.view.file_name():
#           continue

#         line = int(err.group('line'))
#         col = int(err.group('col'))
#         typ = err.group('type')
#         msg = err.group('msg')
#         if err.group('range'):
#           from_line = int(err.group('from_line'))
#           from_col = int(err.group('from_col'))
#           to_line = int(err.group('to_line'))
#           to_col = int(err.group('to_col'))
#           print("{{{}:{}-{}:{}}}".format(from_line, from_col, to_line, to_col))
#           start = self.view.text_point(from_line, from_col)
#           end = self.view.text_point(to_line, to_col)
#           r = sublime.Region(start,end)
#         else:
#           p = self.view.text_point(line, col)
#           r = sublime.Region(p,p+1)
#         if typ == 'warning':
#           warnings.append(r)
#         elif typ == 'error' or typ == 'fatal error':
#           errors.append(r)        
#       print('Warnings:',warnings)
#       print('Errors:',errors)

#       self.view.add_regions("foreground", warnings, "ClangTools.warnings", 'cross', sublime.DRAW_STIPPLED_UNDERLINE)
#       self.view.add_regions("foreground", errors, "ClangTools.errors", 'circle', sublime.DRAW_SOLID_UNDERLINE)

#     except subprocess.CalledProcessError as e:
#       print(str(e))

#   def description(self):
#     return "Format: Clang"
    
class ClangFormatOnSave(sublime_plugin.EventListener):
  def on_pre_save(self, view):
    if not get_setting('format_on_save', False):
      print('no fos')
      return

    syntax = view.settings().get('syntax')
    if syntax in get_setting('supported_syntaxes'):
      view.run_command('clang_format')
  
  # def on_post_save(self, view):
  #   if not get_setting('lint',False):
  #     print('no lint')
  #     return
  #   syntax = view.settings().get('syntax')
  #   if syntax in get_setting('supported_syntaxes'):
  #     view.run_command('clang_lint')

class ClangAutocomplete(sublime_plugin.EventListener):
  def autocomplete(self, view, prefix, locations):
    r = sublime.Region(0, view.size())
    try:
      # just complete first location
      row, col = view.rowcol(locations[0])
      cmd = get_cmd(['-code-completion-at','-:{row}:{col}'.format(row=row+1,col=col), '-']);

      p = subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.PIPE)
      stdoutdata, stderrdata = p.communicate(view.substr(r).encode('utf-8'))
      p.stdin.close()
      results = stdoutdata.decode('utf-8')
      rows = results.splitlines()
      results=[]
      for row in rows:
        pair = row[12:].split(' : ')
        if pair[0] == 'Pattern':
          pair=pair[1:]          

        if len(pair) < 2:
          pair=[pair[0],pair[0]]

        counter = itertools.count(1)
        pair[1]=re.sub("<#([^#]*)#>",lambda m,i=counter: "${{{}:{}}}".format(next(i), m.group(1)),pair[1])
        pair[0]="{}\t{}".format(pair[0],re.sub("\[#|#\]"," ",pair[1]))
        pair[1]=re.sub("\[#[^#]*#\]","",pair[1])

        results.append(pair)

      return results

    except subprocess.CalledProcessError as e:
      print(str(e))

  

  def on_query_completions(self, view, prefix, locations):
    syntax = view.settings().get('syntax')
    if syntax in get_setting('supported_syntaxes'):
      return self.autocomplete(view, prefix, locations)
