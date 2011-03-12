#!/usr/bin/python
#
# Copyright (C) 2009-2010 by Johan De Taeye, frePPLe bvba
#
# This library is free software; you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published
# by the Free Software Foundation; either version 2.1 of the License, or
# (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser
# General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA
#
#  file     : $URL$
#  revision : $LastChangedRevision$  $LastChangedBy$
#  date     : $LastChangedDate$

#
# This python script uses the module unittest to run a series of tests.
#
# Each test has its own subdirectory. In the description below it is referred
# to as {testdir}.
# Three categories of tests are supported.
#
#  - Type 1: Compiled executable
#    If an executable file {testdir} or {testdir}.exe is found in the test
#    directory, the executable is run. The compilation/generation of the
#    executable is not handled by the script, but it's typically done by
#    running the command "make check" in the test subdirectory.
#    The test is successful if both:
#      1) the exit code of the program is 0
#      2) the output of the program is identical to the content of the
#         file {testdir}.expect
#
#  - Type 2: Run a Python test script
#    If a file runtest.py is found in the test directory, it is being run
#    and its exit code is used as the criterium for a successful test.
#
#  - Type 3: Process an XML file
#    If a file {testdir}.xml is found in the test directory, the frepple
#    commandline executable is called to process the file.
#    The test is successful if both:
#      1) the exit code of the program is 0
#      2) the generated output files of the program match the content of the
#         files {testdir}.{nr}.expect
#
#  - If the test subdirectory doesn't match the criteria of any of the above
#    types, the directory is considered not to contain a test.
#
# The script can be run with the following arguments on the command line:
#  - ./runtest.py {test}
#    ./runtest.py {test1} {test2}
#    Execute the tests listed on the command line.
#  - ./runtest.py
#    Execute all tests.
#  - ./runtest.py --vcc
#    Execute all tests using the executables compiled with Microsofts'
#    Visual Studio C++ compiler.
#    Tests of type 1 are skipped in this case.
#

import unittest, os, os.path, getopt, sys, glob
from subprocess import Popen, STDOUT, PIPE

debug = False


# Directory names for tests and frepple_home
testdir = os.path.abspath(os.path.dirname(sys.argv[0]))


def usage():
  # Print help information and exit
  print '\nUsage to run all tests:'
  print '  ./runtest.py [options]\n'
  print 'Usage with list of tests to run:'
  print '  ./runtest.py [options] {test1} {test2} ...\n'
  print 'With the following options:'
  print '  -v  --vcc:'
  print '     Test executables created by Microsoft Visual Studio C++ compiler.'
  print '  -d  --debug:'
  print '     Verbose output of the test.'
  print '  -r  --regression:'
  print '     Run only the tests that are relevant for a regression test.'
  print '     The full test suite also includes some extra tests for testing other aspects.'
  print '  -e  --exclude:'
  print '     Skip a specific test from the suite.'
  print '     This option can be specified multiple times.'


def runTestSuite():
    global debug, testdir    
    if sys.platform in ['windows','win32','win64']:
      platform = 'VCC'
    else:
      platform = 'GCC' 
      
    # Frepple uses the time functions from the C-library, which is senstive to
    # timezone settings. In particular the daylight saving time of different
    # timezones is of interest: it applies only to some timezones, and different
    # timezones switch to summer time at various dates.
    # The next statement makes sure the test are all running with the same timezone,
    # and in addition a timezone without DST.
    os.environ['TZ'] = 'EST'

    # Parse the command line
    opts = []
    tests = []
    excluded = []
    try:
        opts, args = getopt.getopt(sys.argv[1:], "dvhre:", ["debug", "vcc", "help", "regression", "exclude="])
    except getopt.GetoptError:
      usage()
      sys.exit(1)
    for o, a in opts:
      if o in ("-r", "--regression"):
        # THE HARD_CODED TESTS LISTED HERE ARE SKIPPED WHEN RUNNING A REGRESSION TEST.
        # These test verify other aspects of the application.
        excluded = ["xml_remote", "scalability_1", "scalability_2", "scalability_3", "forecast_6", "jobshop", "multithreading"]
        break
    for o, a in opts:
      if o in ("-v" "--vcc"):
        # Use executables generated by the Visual C++ compiler
        platform = 'VCC'
      elif o in ("-d", "--debug"):
        debug = True
      elif o in ("-e", "--exclude"):
        excluded.append(a)
      elif o in ("-h", "--help"):
        # Print help information and exit
        usage()
        sys.exit(1)
    for i in args:
      tests.extend(glob.glob(i))

    # Executable to run
    os.environ['FREPPLE_HOME'] = os.path.join(testdir,"..","bin")
    if platform == 'VCC':
      os.environ['EXECUTABLE'] = '"' + os.path.join(testdir,"..","bin","frepple.exe") + '"'
    else:
      # Executable to be used for the tests. Exported as an environment variable.
      # This default executable is the one valid  for GCC cygwin and GCC *nux builds.
      os.environ['EXECUTABLE'] = '"%s" --mode=execute %s' % (os.path.join(testdir,"..","libtool"), os.path.join(testdir,"..","src","frepple"))

    # Argh... Special cases for that special platform again...
    if 'FREPPLE_HOME' in os.environ:
      if sys.platform == 'cygwin' and platform == 'VCC':
        # Test running with cygwin python but testing the vcc executable
        os.environ['FREPPLE_HOME'] = Popen(
          "cygpath  --windows " + os.environ['FREPPLE_HOME'],
          stdout=PIPE, shell=True).communicate()[0].strip()
      if sys.platform == 'win32' and platform == 'GCC':
        # Test running with windows python but testing the cygwin executable
        os.environ['FREPPLE_HOME'] = Popen(
          "cygpath  --unix " + os.environ['FREPPLE_HOME'],
          stdout=PIPE, shell=True).communicate()[0].strip()

    # Update the search path for shared libraries, such that the modules
    # can be picked up.
    #  LD_LIBRARY_PATH variable for Linux, Solaris
    #  LIBPATH for AIX
    #  SHLIB_PATH for HPUX
    #  PATH for windows, cygwin
    # We set all variables anyway.
    if 'FREPPLE_HOME' in os.environ:
      for var in ('LD_LIBRARY_PATH','LIBPATH','SHLIB_PATH','PATH'):
        if var in os.environ:
          os.environ[var] += os.pathsep + os.environ['FREPPLE_HOME']
        else:
          os.environ[var] = os.environ['FREPPLE_HOME']

    # Define a list with tests to run
    if len(tests) == 0:
        # No tests specified, so run them all
        subdirs = os.listdir(testdir)
        subdirs.sort()
        for i in subdirs:
            if i == '.svn' or os.path.isfile(i): continue
            tests.append(i)
    else:
        # A list of tests has been specified, and we now validate it
        for i in tests:
            if not os.path.isdir(os.path.join(testdir, i)):
                print "Warning: Test directory " + i + " doesn't exist"
                tests.remove(i)

    # Now define the test suite
    AllTests = unittest.TestSuite()
    for i in tests:
        
        # Skip excluded tests
        if i in excluded: continue
        
        # Expand to directory names
        i = os.path.normpath(i)
        tmp = os.path.join(testdir, i, i)

        # Only GCC runs compiled tests
        if len(glob.glob(os.path.join(testdir, i, '*.cpp'))) > 0 and platform != "GCC":
          continue

        # Check the test type
        if os.path.isfile(tmp) or os.path.isfile(tmp + '.exe'):
            # Type 1: (compiled) executable
            AllTests.addTest(freppleTest(i, 'runExecutable'))
        elif os.path.isfile(os.path.join(testdir, i, 'runtest.py')):
            # Type 2: perl script runtest.pl available
            AllTests.addTest(freppleTest(i, 'runScript'))
        elif os.path.isfile(tmp + '.xml'):
            # Type 3: input xml file specified
            AllTests.addTest(freppleTest(i, 'runXML'))
        else:
            # Undetermined - not a test directory
            print "Warning: Unrecognized test in directory " + i

    # Finally, run the test suite now
    if 'FREPPLE_HOME' in os.environ:
      print "Running", AllTests.countTestCases(), \
         "tests from directory", testdir, \
         "with FREPPLE_HOME", os.environ['FREPPLE_HOME']
    else:
      print "Running", AllTests.countTestCases(), \
         "tests from directory", testdir
    result = unittest.TextTestRunner(verbosity=2,descriptions=False).run(AllTests)
    if not result.wasSuccessful(): sys.exit(1)
    

class freppleTest (unittest.TestCase):
    def __init__(self, directoryname, methodName):
        self.subdirectory = directoryname
        super(freppleTest, self).__init__(methodName)

    def setUp(self):
        global testdir
        os.chdir(os.path.join(testdir, self.subdirectory))

    def __str__(self):
        ''' Use the directory name as the test name.'''
        return self.subdirectory

    def runProcess(self, cmd):
        '''Run a child process.'''
        global debug, testdir
        try:
            if debug:
              o = None
              print "\nOutput:"
            else:
              o = PIPE
            proc = Popen(cmd,
                bufsize = 0,
                stdout = o,
                stderr = STDOUT,
                universal_newlines = True,
                shell = True,
                )
            if not debug:
              # Because the process doesn't stop until we've read the pipe.
              proc.communicate()
            res = proc.wait()
            if res: self.assertFalse("Exit code non-zero")
        except KeyboardInterrupt:
            # The test has been interupted, which counts as a failure
            self.assertFalse("Interrupted test")

    def runExecutable(self):
        '''Running a compiled executable'''
        # Run the command and verify exit code
        self.runProcess("./" + self.subdirectory + " >test.out")

        # Verify the output
        if os.path.isfile(self.subdirectory + ".expect"):
            if not os.path.isfile("test.out"):
              self.fail("Missing output file")
            elif diff("test.out", self.subdirectory + ".expect"):
                self.assertFalse("Difference in output")

    def runScript(self):
        '''Running a test script'''
        self.runProcess('python %s' % os.path.join('.','runtest.py'))

    def runXML(self):
        '''Running the command line tool with an XML file as argument.'''
        global debug

        # Delete previous output
        self.output = glob.glob("output.*.xml")
        self.output.extend(glob.glob("output.*.txt"))
        self.output.extend(glob.glob("output.*.tmp"))
        for i in self.output: os.remove(i)

        # Run the executable
        self.runProcess(os.environ['EXECUTABLE'] + " -validate " + self.subdirectory + ".xml")

        # Now check the output file, if there is an expected output given
        nr = 1;
        while os.path.isfile(self.subdirectory + "." + str(nr) + ".expect"):
            if os.path.isfile("output."+str(nr)+".xml"):
                if debug: print "Comparing expected and actual output", nr
                if diff(self.subdirectory + "." + str(nr) + ".expect", \
                        "output."+str(nr)+".xml"):
                    self.assertFalse("Difference in output " + str(nr), "Difference in output " + str(nr))
            else:
                self.assertFalse('Missing frePPLe output file ' + str(nr), 'Missing frePPLe output file ' + str(nr))
            nr += 1;

def diff(f1, f2):
  '''
  Compares 2 text files and returns True if they are different.
  The default one in the package isn't doing the job for us: we want to
  ignore differences in the file ending.
  '''
  fp1 = open(f1, 'rt')
  fp2 = open(f2, 'rt')
  while True:
    b1 = fp1.readline()
    b2 = fp2.readline()
    if b1.strip() != b2.strip(): return True
    if not b1: return False

# If the file is processed as a script, run the test suite.
# Otherwise, only define the methods.
if __name__ == "__main__": runTestSuite()
